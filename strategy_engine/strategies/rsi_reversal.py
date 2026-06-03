from decimal import Decimal

import pandas as pd
import pandas_ta as ta

from strategy_engine.base_strategy import BaseStrategy
from strategy_engine.signal import Direction, Signal


class RSIReversal(BaseStrategy):
    name = "rsi_reversal"
    timeframe = "1hr"

    def __init__(
        self,
        rsi_period: int = 14,
        bb_period: int = 20,
        bb_std: float = 2.0,
        rsi_oversold: float = 30.0,
        rsi_overbought: float = 70.0,
    ) -> None:
        self._rsi_period = rsi_period
        self._bb_period = bb_period
        self._bb_std = bb_std
        self._rsi_oversold = rsi_oversold
        self._rsi_overbought = rsi_overbought

    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df["rsi"] = ta.rsi(df["close"], length=self._rsi_period)
        bbands = ta.bbands(df["close"], length=self._bb_period, std=self._bb_std)
        if bbands is not None:
            df["bb_lower"] = bbands.iloc[:, 0]
            df["bb_mid"] = bbands.iloc[:, 1]
            df["bb_upper"] = bbands.iloc[:, 2]
        return df

    def generate_signal(self, df: pd.DataFrame) -> Signal | None:
        min_rows = max(self._rsi_period, self._bb_period) + 2
        if len(df) < min_rows:
            return None

        if "rsi" not in df.columns or "bb_lower" not in df.columns:
            return None

        curr_rsi = df["rsi"].iloc[-1]
        prev_rsi = df["rsi"].iloc[-2]
        curr_close = float(df["close"].iloc[-1])
        bb_lower = df["bb_lower"].iloc[-1]
        bb_upper = df["bb_upper"].iloc[-1]

        if pd.isna(curr_rsi) or pd.isna(prev_rsi) or pd.isna(bb_lower) or pd.isna(bb_upper):
            return None

        price = Decimal(str(df["close"].iloc[-1]))
        timestamp = df["timestamp"].iloc[-1]
        symbol = df["symbol"].iloc[0] if "symbol" in df.columns else "UNKNOWN"

        # Bullish reversal: RSI crosses above oversold AND price near/below lower BB
        if prev_rsi <= self._rsi_oversold and curr_rsi > self._rsi_oversold:
            if curr_close <= float(bb_lower) * 1.01:
                stop_loss = price * Decimal("0.97")  # 3% below
                return Signal(
                    strategy_name=self.name,
                    symbol=symbol,
                    direction=Direction.BUY,
                    price=price,
                    timestamp=timestamp,
                    stop_loss=stop_loss,
                    metadata={"rsi": float(curr_rsi), "bb_lower": float(bb_lower)},
                )

        # Bearish reversal: RSI crosses below overbought AND price near/above upper BB
        if prev_rsi >= self._rsi_overbought and curr_rsi < self._rsi_overbought:
            if curr_close >= float(bb_upper) * 0.99:
                stop_loss = price * Decimal("1.03")  # 3% above
                return Signal(
                    strategy_name=self.name,
                    symbol=symbol,
                    direction=Direction.SELL,
                    price=price,
                    timestamp=timestamp,
                    stop_loss=stop_loss,
                    metadata={"rsi": float(curr_rsi), "bb_upper": float(bb_upper)},
                )

        return None
