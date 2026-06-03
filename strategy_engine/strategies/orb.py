from datetime import time
from decimal import Decimal

import pandas as pd

from config.constants import IST
from strategy_engine.base_strategy import BaseStrategy
from strategy_engine.signal import Direction, Signal

ORB_START = time(9, 15)
ORB_END = time(9, 30)


class OpeningRangeBreakout(BaseStrategy):
    name = "orb"
    timeframe = "5min"

    def __init__(self, volume_multiplier: float = 1.5) -> None:
        self._volume_multiplier = volume_multiplier
        self._range_high: Decimal | None = None
        self._range_low: Decimal | None = None
        self._range_set = False
        self._avg_volume: float = 0.0
        self._signal_fired_today = False
        self._current_date: str = ""

    def _reset_for_new_day(self, date_str: str) -> None:
        self._range_high = None
        self._range_low = None
        self._range_set = False
        self._avg_volume = 0.0
        self._signal_fired_today = False
        self._current_date = date_str

    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        return df

    def generate_signal(self, df: pd.DataFrame) -> Signal | None:
        if len(df) < 2:
            return None

        last = df.iloc[-1]
        timestamp = last["timestamp"]
        if hasattr(timestamp, "date"):
            date_str = str(timestamp.date())
        else:
            date_str = str(timestamp)[:10]

        if date_str != self._current_date:
            self._reset_for_new_day(date_str)

        if hasattr(timestamp, "time"):
            candle_time = timestamp.time()
        else:
            return None

        high = Decimal(str(last["high"]))
        low = Decimal(str(last["low"]))
        close = Decimal(str(last["close"]))
        volume = int(last["volume"])

        # Build the opening range (9:15 to 9:30)
        if ORB_START <= candle_time < ORB_END:
            if self._range_high is None or high > self._range_high:
                self._range_high = high
            if self._range_low is None or low < self._range_low:
                self._range_low = low

            # Accumulate volume for average
            orb_candles = df[df["timestamp"].apply(
                lambda t: hasattr(t, "time") and ORB_START <= t.time() < ORB_END
                and str(t.date()) == date_str
            )]
            if len(orb_candles) > 0:
                self._avg_volume = float(orb_candles["volume"].mean())
            return None

        if candle_time < ORB_END:
            return None

        if not self._range_set and self._range_high is not None:
            self._range_set = True

        if not self._range_set or self._range_high is None or self._range_low is None:
            return None

        if self._signal_fired_today:
            return None

        symbol = last.get("symbol", "UNKNOWN") if isinstance(last, dict) else (
            last["symbol"] if "symbol" in df.columns else "UNKNOWN"
        )

        # Bullish breakout: close above range high with volume confirmation
        if close > self._range_high and volume > self._avg_volume * self._volume_multiplier:
            self._signal_fired_today = True
            return Signal(
                strategy_name=self.name,
                symbol=symbol,
                direction=Direction.BUY,
                price=close,
                timestamp=timestamp,
                stop_loss=self._range_low,
                metadata={
                    "range_high": str(self._range_high),
                    "range_low": str(self._range_low),
                    "volume": volume,
                    "avg_volume": self._avg_volume,
                },
            )

        # Bearish breakout: close below range low with volume confirmation
        if close < self._range_low and volume > self._avg_volume * self._volume_multiplier:
            self._signal_fired_today = True
            return Signal(
                strategy_name=self.name,
                symbol=symbol,
                direction=Direction.SELL,
                price=close,
                timestamp=timestamp,
                stop_loss=self._range_high,
                metadata={
                    "range_high": str(self._range_high),
                    "range_low": str(self._range_low),
                    "volume": volume,
                    "avg_volume": self._avg_volume,
                },
            )

        return None
