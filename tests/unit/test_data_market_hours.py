from datetime import date, datetime

from config.constants import IST
from data_ingestion.market_hours import (
    is_market_open,
    is_trading_day,
    should_websocket_connect,
)


def test_market_hours__weekday__is_trading_day() -> None:
    monday = date(2026, 6, 1)  # Monday
    assert is_trading_day(monday) is True


def test_market_hours__saturday__not_trading_day() -> None:
    saturday = date(2026, 5, 30)  # Saturday
    assert is_trading_day(saturday) is False


def test_market_hours__sunday__not_trading_day() -> None:
    sunday = date(2026, 5, 31)  # Sunday
    assert is_trading_day(sunday) is False


def test_market_hours__holiday__not_trading_day() -> None:
    republic_day = date(2026, 1, 26)
    assert is_trading_day(republic_day) is False


def test_market_hours__during_hours__market_open() -> None:
    dt = datetime(2026, 6, 1, 10, 30, 0, tzinfo=IST)  # Monday 10:30 AM
    assert is_market_open(dt) is True


def test_market_hours__before_open__market_closed() -> None:
    dt = datetime(2026, 6, 1, 9, 0, 0, tzinfo=IST)  # Monday 9:00 AM
    assert is_market_open(dt) is False


def test_market_hours__after_close__market_closed() -> None:
    dt = datetime(2026, 6, 1, 15, 31, 0, tzinfo=IST)  # Monday 3:31 PM
    assert is_market_open(dt) is False


def test_websocket__should_connect_at_914() -> None:
    dt = datetime(2026, 6, 1, 9, 14, 0, tzinfo=IST)
    assert should_websocket_connect(dt) is True


def test_websocket__should_not_connect_at_800() -> None:
    dt = datetime(2026, 6, 1, 8, 0, 0, tzinfo=IST)
    assert should_websocket_connect(dt) is False


def test_websocket__should_not_connect_on_holiday() -> None:
    dt = datetime(2026, 1, 26, 10, 0, 0, tzinfo=IST)
    assert should_websocket_connect(dt) is False
