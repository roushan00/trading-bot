import structlog

from strategy_engine.base_strategy import BaseStrategy
from strategy_engine.signal import Signal
from strategy_engine.signal_queue import SignalQueue

import pandas as pd

logger = structlog.get_logger(__name__)


class StrategyRunner:
    def __init__(self, strategies: list[BaseStrategy], signal_queue: SignalQueue) -> None:
        self._strategies = strategies
        self._signal_queue = signal_queue
        self._candle_buffers: dict[str, dict[str, pd.DataFrame]] = {}

    def _get_buffer_key(self, strategy: BaseStrategy, symbol: str) -> tuple[str, str]:
        return strategy.name, f"{symbol}:{strategy.timeframe}"

    async def on_candle(self, symbol: str, timeframe: str, candle_row: dict) -> list[Signal]:
        signals: list[Signal] = []

        for strategy in self._strategies:
            if strategy.timeframe != timeframe:
                continue

            buf_key = f"{symbol}:{timeframe}"
            if strategy.name not in self._candle_buffers:
                self._candle_buffers[strategy.name] = {}

            if buf_key not in self._candle_buffers[strategy.name]:
                self._candle_buffers[strategy.name][buf_key] = pd.DataFrame(
                    columns=["timestamp", "open", "high", "low", "close", "volume"]
                )

            df = self._candle_buffers[strategy.name][buf_key]
            new_row = pd.DataFrame([candle_row])
            df = pd.concat([df, new_row], ignore_index=True)

            max_rows = 200
            if len(df) > max_rows:
                df = df.iloc[-max_rows:].reset_index(drop=True)

            self._candle_buffers[strategy.name][buf_key] = df

            try:
                signal = strategy.on_candle(df.copy())
                if signal is not None:
                    await self._signal_queue.push(signal)
                    signals.append(signal)
                    logger.info(
                        "signal_generated",
                        strategy=strategy.name,
                        symbol=symbol,
                        direction=signal.direction.value,
                        price=str(signal.price),
                    )
            except Exception:
                logger.error(
                    "strategy_error",
                    strategy=strategy.name,
                    symbol=symbol,
                    exc_info=True,
                )

        return signals
