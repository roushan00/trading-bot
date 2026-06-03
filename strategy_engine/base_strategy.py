from abc import ABC, abstractmethod

import pandas as pd

from strategy_engine.signal import Signal


class BaseStrategy(ABC):
    name: str = "unnamed"
    timeframe: str = "15min"

    @abstractmethod
    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        ...

    @abstractmethod
    def generate_signal(self, df: pd.DataFrame) -> Signal | None:
        ...

    def on_candle(self, df: pd.DataFrame) -> Signal | None:
        df = self.compute_indicators(df)
        return self.generate_signal(df)
