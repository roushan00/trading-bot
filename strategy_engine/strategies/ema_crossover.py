from decimal import Decimal

import pandas as pd
import pandas_ta as ta

from strategy_engine.base_strategy import BaseStrategy
from strategy_engine.signal import Direction, Signal


class EMACrossover(BaseStrategy):
    name = "ema_crossover"
    timeframe = "15min"

    def __init__(self, fast_period: int = 9, slow_period: int = 21) -> None:
        self._fast_period = fast_period
        self._slow_period = slow_period

    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df[f"ema_{self._fast_period}"] = ta.ema(df["close"], length=self._fast_period)
        df[f"ema_{self._slow_period}"] = ta.ema(df["close"], length=self._slow_period)
        return df

    def generate_signal(self, df: pd.DataFrame) -> Signal | None:
        if len(df) < self._slow_period + 2:
            return None

        fast_col = f"ema_{self._fast_period}"
        slow_col = f"ema_{self._slow_period}"

        curr_fast = df[fast_col].iloc[-1]
        curr_slow = df[slow_col].iloc[-1]
        prev_fast = df[fast_col].iloc[-2]
        prev_slow = df[slow_col].iloc[-2]

        if pd.isna(curr_fast) or pd.isna(curr_slow) or pd.isna(prev_fast) or pd.isna(prev_slow):
            return None

        price = Decimal(str(df["close"].iloc[-1]))
        timestamp = df["timestamp"].iloc[-1]

        # Golden cross: fast crosses above slow (with confirmation candle)
        if prev_fast <= prev_slow and curr_fast > curr_slow:
            # Confirmation: current close is above both EMAs
            close_val = float(df["close"].iloc[-1])
            if close_val > curr_fast and close_val > curr_slow:
                stop_loss = price * Decimal("0.98")  # 2% below
                return Signal(
                    strategy_name=self.name,
                    symbol=df.get("symbol", pd.Series(["UNKNOWN"])).iloc[0] if "symbol" in df.columns else "UNKNOWN",
                    direction=Direction.BUY,
                    price=price,
                    timestamp=timestamp,
                    stop_loss=stop_loss,
                    metadata={"fast_ema": float(curr_fast), "slow_ema": float(curr_slow)},
                )

        # Death cross: fast crosses below slow (with confirmation candle)
        if prev_fast >= prev_slow and curr_fast < curr_slow:
            close_val = float(df["close"].iloc[-1])
            if close_val < curr_fast and close_val < curr_slow:
                stop_loss = price * Decimal("1.02")  # 2% above
                return Signal(
                    strategy_name=self.name,
                    symbol=df.get("symbol", pd.Series(["UNKNOWN"])).iloc[0] if "symbol" in df.columns else "UNKNOWN",
                    direction=Direction.SELL,
                    price=price,
                    timestamp=timestamp,
                    stop_loss=stop_loss,
                    metadata={"fast_ema": float(curr_fast), "slow_ema": float(curr_slow)},
                )

        return None
