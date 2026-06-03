from datetime import date, datetime

import structlog

from config.constants import (
    IST,
    MARKET_CLOSE,
    MARKET_OPEN,
    NSE_HOLIDAYS_2026,
    WEBSOCKET_START,
    WEBSOCKET_STOP,
)

logger = structlog.get_logger(__name__)

_HOLIDAY_DATES: set[date] = {
    date.fromisoformat(d) for d in NSE_HOLIDAYS_2026
}


def is_trading_day(d: date | None = None) -> bool:
    if d is None:
        d = datetime.now(tz=IST).date()
    if d.weekday() >= 5:
        return False
    if d in _HOLIDAY_DATES:
        return False
    return True


def is_market_open(now: datetime | None = None) -> bool:
    if now is None:
        now = datetime.now(tz=IST)
    if not is_trading_day(now.date()):
        return False
    current_time = now.timetz()
    return MARKET_OPEN <= current_time <= MARKET_CLOSE


def should_websocket_connect(now: datetime | None = None) -> bool:
    if now is None:
        now = datetime.now(tz=IST)
    if not is_trading_day(now.date()):
        return False
    current_time = now.timetz()
    return WEBSOCKET_START <= current_time <= WEBSOCKET_STOP


def seconds_until_websocket_start(now: datetime | None = None) -> float:
    if now is None:
        now = datetime.now(tz=IST)
    ws_start_dt = now.replace(
        hour=WEBSOCKET_START.hour,
        minute=WEBSOCKET_START.minute,
        second=0,
        microsecond=0,
    )
    if now >= ws_start_dt:
        return 0.0
    return (ws_start_dt - now).total_seconds()
