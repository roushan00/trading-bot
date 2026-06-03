from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Callable

import structlog

from config.constants import IST
from data_ingestion.normalizer import Tick

logger = structlog.get_logger(__name__)

TIMEFRAME_MINUTES = {
    "1min": 1,
    "5min": 5,
    "15min": 15,
    "1hr": 60,
}


@dataclass
class CandleAccumulator:
    symbol: str
    timeframe: str
    period_start: datetime
    open: Decimal = Decimal("0")
    high: Decimal = Decimal("-Infinity")
    low: Decimal = Decimal("Infinity")
    close: Decimal = Decimal("0")
    volume: int = 0
    tick_count: int = 0

    def add_tick(self, tick: Tick) -> None:
        if self.tick_count == 0:
            self.open = tick.ltp
        if tick.ltp > self.high:
            self.high = tick.ltp
        if tick.ltp < self.low:
            self.low = tick.ltp
        self.close = tick.ltp
        self.volume += tick.volume
        self.tick_count += 1

    def is_empty(self) -> bool:
        return self.tick_count == 0


@dataclass(frozen=True, slots=True)
class Candle:
    symbol: str
    timeframe: str
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int


class CandleBuilder:
    def __init__(self, timeframes: list[str] | None = None, on_candle: Callable[[Candle], None] | None = None) -> None:
        self._timeframes = timeframes or ["1min", "5min", "15min"]
        self._on_candle = on_candle
        self._accumulators: dict[str, dict[str, CandleAccumulator]] = defaultdict(dict)

    def _get_period_start(self, timestamp: datetime, timeframe: str) -> datetime:
        minutes = TIMEFRAME_MINUTES[timeframe]
        total_minutes = timestamp.hour * 60 + timestamp.minute
        period_minute = (total_minutes // minutes) * minutes
        return timestamp.replace(
            hour=period_minute // 60,
            minute=period_minute % 60,
            second=0,
            microsecond=0,
        )

    def _get_period_end(self, period_start: datetime, timeframe: str) -> datetime:
        minutes = TIMEFRAME_MINUTES[timeframe]
        return period_start + timedelta(minutes=minutes)

    def on_tick(self, tick: Tick) -> list[Candle]:
        completed: list[Candle] = []

        for tf in self._timeframes:
            key = f"{tick.symbol}:{tf}"
            period_start = self._get_period_start(tick.timestamp, tf)

            acc = self._accumulators.get(tick.symbol, {}).get(tf)

            if acc is not None and acc.period_start != period_start:
                if not acc.is_empty():
                    candle = Candle(
                        symbol=acc.symbol,
                        timeframe=acc.timeframe,
                        timestamp=acc.period_start,
                        open=acc.open,
                        high=acc.high,
                        low=acc.low,
                        close=acc.close,
                        volume=acc.volume,
                    )
                    completed.append(candle)
                    logger.debug("candle_completed", symbol=candle.symbol, timeframe=tf, timestamp=str(candle.timestamp))
                    if self._on_candle:
                        self._on_candle(candle)
                acc = None

            if acc is None:
                acc = CandleAccumulator(
                    symbol=tick.symbol,
                    timeframe=tf,
                    period_start=period_start,
                )
                if tick.symbol not in self._accumulators:
                    self._accumulators[tick.symbol] = {}
                self._accumulators[tick.symbol][tf] = acc

            acc.add_tick(tick)

        return completed

    def flush_all(self) -> list[Candle]:
        completed: list[Candle] = []
        for symbol_accs in self._accumulators.values():
            for tf, acc in symbol_accs.items():
                if not acc.is_empty():
                    candle = Candle(
                        symbol=acc.symbol,
                        timeframe=acc.timeframe,
                        timestamp=acc.period_start,
                        open=acc.open,
                        high=acc.high,
                        low=acc.low,
                        close=acc.close,
                        volume=acc.volume,
                    )
                    completed.append(candle)
                    if self._on_candle:
                        self._on_candle(candle)
        self._accumulators.clear()
        return completed
