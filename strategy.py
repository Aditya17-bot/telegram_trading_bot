# =============================================================================
# strategy.py — The signal engine. Checks every stock every minute.
# Applies 3 filters before generating a trade signal:
#   1. Volume filter  — breakout candle volume > 1.5× 20-day average
#   2. Pullback filter — price retraces slightly after breakout
#   3. EMA filter     — for bull breaks, price must be above 20 EMA
# =============================================================================

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict
import logging

from config import (
    VOLUME_MULTIPLIER, PULLBACK_PCT, STOP_LOSS_PCT,
    TARGET_RR, EMA_PERIOD
)

log = logging.getLogger(__name__)


@dataclass
class Signal:
    symbol: str
    direction: str          # "BUY" or "SELL"
    entry_price: float
    stop_loss: float
    target: float
    trigger_reason: str
    pdh: float
    pdl: float
    generated_at: datetime = field(default_factory=datetime.now)

    def __str__(self):
        return (
            f"[{self.direction}] {self.symbol} | "
            f"Entry: {self.entry_price:.2f} | "
            f"SL: {self.stop_loss:.2f} | "
            f"Target: {self.target:.2f} | "
            f"Reason: {self.trigger_reason}"
        )


class BreakoutTracker:
    """
    Tracks each stock's breakout state across the day.
    A breakout goes through stages:
      idle → broken_up / broken_down → pulling_back → signal_ready
    """

    def __init__(self, symbol: str, levels: dict):
        self.symbol = symbol
        self.pdh = levels["pdh"]
        self.pdl = levels["pdl"]
        self.pdc = levels["pdc"]
        self.avg_volume = levels["avg_volume"]
        self.ema20 = levels["ema20"]

        # State machine
        self.state = "idle"          # idle | broken_up | broken_down | done
        self.breakout_price = None   # Price at which break occurred
        self.breakout_volume = None  # Volume at breakout candle
        self.signal_generated = False

    def update(self, ltp: float, current_volume: float, candle_volume: float) -> Optional[Signal]:
        """
        Call this every minute with fresh price and volume data.
        Returns a Signal if all conditions are met, else None.

        ltp            : Last Traded Price (current price)
        current_volume : Total volume traded so far today
        candle_volume  : Volume of the most recent candle
        """

        if self.signal_generated:
            return None  # Only one signal per stock per day

        # ---------------------------------------------------------------
        # PHASE 1: Detect the breakout
        # ---------------------------------------------------------------
        if self.state == "idle":

            # Bull breakout: price closes above PDH
            if ltp > self.pdh:
                vol_ok = candle_volume > self.avg_volume * VOLUME_MULTIPLIER
                ema_ok = ltp > self.ema20  # EMA trend filter

                if vol_ok and ema_ok:
                    self.state = "broken_up"
                    self.breakout_price = ltp
                    self.breakout_volume = candle_volume
                    log.info(
                        f"{self.symbol}: BULL BREAK above PDH {self.pdh:.2f} "
                        f"at {ltp:.2f} | Vol {candle_volume:,.0f} vs avg {self.avg_volume:,.0f} ✓"
                    )
                elif not vol_ok:
                    log.debug(
                        f"{self.symbol}: Break above PDH but LOW VOLUME "
                        f"({candle_volume:,.0f} < {self.avg_volume * VOLUME_MULTIPLIER:,.0f}) — skipping"
                    )
                elif not ema_ok:
                    log.debug(
                        f"{self.symbol}: Break above PDH but BELOW EMA20 "
                        f"({ltp:.2f} < {self.ema20:.2f}) — skipping"
                    )

            # Bear breakout: price closes below PDL
            elif ltp < self.pdl:
                vol_ok = candle_volume > self.avg_volume * VOLUME_MULTIPLIER

                if vol_ok:
                    self.state = "broken_down"
                    self.breakout_price = ltp
                    self.breakout_volume = candle_volume
                    log.info(
                        f"{self.symbol}: BEAR BREAK below PDL {self.pdl:.2f} "
                        f"at {ltp:.2f} | Vol {candle_volume:,.0f} vs avg {self.avg_volume:,.0f} ✓"
                    )
                    # Note: No EMA filter for short side — bear breaks work regardless of EMA
                else:
                    log.debug(
                        f"{self.symbol}: Break below PDL but LOW VOLUME — skipping"
                    )

        # ---------------------------------------------------------------
        # PHASE 2: Wait for pullback after bull break
        # ---------------------------------------------------------------
        elif self.state == "broken_up":
            pullback_threshold = self.pdh * (1 + PULLBACK_PCT)
            # We want price to have pulled back toward PDH (not still running away)
            # Entry condition: price came back within PULLBACK_PCT above PDH
            if ltp <= pullback_threshold:
                log.info(
                    f"{self.symbol}: Pullback to {ltp:.2f} after bull break "
                    f"(threshold: {pullback_threshold:.2f}) — SIGNAL READY"
                )
                self.signal_generated = True
                self.state = "done"

                entry = ltp
                sl = entry * (1 - STOP_LOSS_PCT)
                sl_distance = entry - sl
                target = entry + (sl_distance * TARGET_RR)

                return Signal(
                    symbol=self.symbol,
                    direction="BUY",
                    entry_price=round(entry, 2),
                    stop_loss=round(sl, 2),
                    target=round(target, 2),
                    trigger_reason=f"PDH {self.pdh:.2f} broken + pullback",
                    pdh=self.pdh,
                    pdl=self.pdl,
                )

            # Fake breakout trap: if price drops BELOW PDH after breaking it
            # Smart money faked out retail — abort this trade
            elif ltp < self.pdh * 0.999:
                log.warning(
                    f"{self.symbol}: FAKE BREAKOUT detected — price fell back below PDH "
                    f"{self.pdh:.2f}. Aborting."
                )
                self.state = "idle"  # Reset — don't trade this stock today
                self.signal_generated = True  # Mark done so we don't re-enter

        # ---------------------------------------------------------------
        # PHASE 2: Wait for pullback after bear break
        # ---------------------------------------------------------------
        elif self.state == "broken_down":
            pullback_threshold = self.pdl * (1 - PULLBACK_PCT)
            # Price should bounce back UP toward PDL for retest entry
            if ltp >= pullback_threshold:
                log.info(
                    f"{self.symbol}: Retest to {ltp:.2f} after bear break "
                    f"(threshold: {pullback_threshold:.2f}) — SIGNAL READY"
                )
                self.signal_generated = True
                self.state = "done"

                entry = ltp
                sl = entry * (1 + STOP_LOSS_PCT)  # SL above entry for short
                sl_distance = sl - entry
                target = entry - (sl_distance * TARGET_RR)

                return Signal(
                    symbol=self.symbol,
                    direction="SELL",
                    entry_price=round(entry, 2),
                    stop_loss=round(sl, 2),
                    target=round(target, 2),
                    trigger_reason=f"PDL {self.pdl:.2f} broken + retest",
                    pdh=self.pdh,
                    pdl=self.pdl,
                )

            # Fake bear breakout: price recovered strongly above PDL
            elif ltp > self.pdl * 1.001:
                log.warning(
                    f"{self.symbol}: FAKE BEAR BREAKOUT — price recovered above PDL. Aborting."
                )
                self.state = "idle"
                self.signal_generated = True

        return None


class SignalEngine:
    """
    Manages BreakoutTrackers for all symbols.
    Call scan() every minute with fresh quote data.
    """

    def __init__(self, levels: dict):
        self.trackers: Dict[str, BreakoutTracker] = {}
        for symbol, lvl in levels.items():
            self.trackers[symbol] = BreakoutTracker(symbol, lvl)
        log.info(f"Signal engine initialized for {len(self.trackers)} symbols.")

    def scan(self, quotes: dict) -> list[Signal]:
        """
        quotes: dict of {symbol: {"ltp": float, "volume": int, "last_candle_volume": int}}
        Returns list of new signals generated this scan.
        """
        signals = []
        for symbol, tracker in self.trackers.items():
            if symbol not in quotes:
                continue
            q = quotes[symbol]
            signal = tracker.update(
                ltp=q["ltp"],
                current_volume=q.get("volume", 0),
                candle_volume=q.get("last_candle_volume", 0),
            )
            if signal:
                log.info(f"SIGNAL GENERATED: {signal}")
                signals.append(signal)
        return signals

    def get_status(self) -> dict:
        """Returns current state of all trackers — useful for monitoring."""
        return {
            sym: tracker.state
            for sym, tracker in self.trackers.items()
        }