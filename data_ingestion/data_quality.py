from datetime import datetime, timedelta

import structlog

from config.constants import IST

logger = structlog.get_logger(__name__)

GAP_THRESHOLD_SECONDS = 300  # 5 minutes


class DataQualityMonitor:
    def __init__(self, gap_threshold_seconds: int = GAP_THRESHOLD_SECONDS) -> None:
        self._last_tick_time: dict[str, datetime] = {}
        self._gap_threshold = timedelta(seconds=gap_threshold_seconds)
        self._gap_count: dict[str, int] = {}

    def on_tick(self, symbol: str, timestamp: datetime) -> None:
        last = self._last_tick_time.get(symbol)
        if last is not None:
            gap = timestamp - last
            if gap > self._gap_threshold:
                self._gap_count[symbol] = self._gap_count.get(symbol, 0) + 1
                logger.warning(
                    "data_gap_detected",
                    symbol=symbol,
                    gap_seconds=gap.total_seconds(),
                    last_tick=last.isoformat(),
                    current_tick=timestamp.isoformat(),
                    total_gaps=self._gap_count[symbol],
                )
        self._last_tick_time[symbol] = timestamp

    def get_gap_count(self, symbol: str) -> int:
        return self._gap_count.get(symbol, 0)

    def get_last_tick_time(self, symbol: str) -> datetime | None:
        return self._last_tick_time.get(symbol)

    def reset(self) -> None:
        self._last_tick_time.clear()
        self._gap_count.clear()
