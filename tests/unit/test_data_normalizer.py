from datetime import datetime
from decimal import Decimal

from config.constants import IST
from data_ingestion.normalizer import Tick


def test_tick__from_dict__creates_valid_tick() -> None:
    data = {
        "symbol": "RELIANCE",
        "token": "2885",
        "ltp": "2450.50",
        "open": "2440.00",
        "high": "2460.00",
        "low": "2435.00",
        "close": "2445.00",
        "volume": 100000,
        "timestamp": "2026-05-28T10:30:00+05:30",
    }
    tick = Tick.from_dict(data)
    assert tick.symbol == "RELIANCE"
    assert tick.ltp == Decimal("2450.50")
    assert tick.volume == 100000
    assert tick.timestamp.tzinfo is not None


def test_tick__to_dict__roundtrip() -> None:
    ts = datetime(2026, 5, 28, 10, 30, 0, tzinfo=IST)
    tick = Tick(
        symbol="INFY",
        token="1594",
        ltp=Decimal("1500.25"),
        open=Decimal("1490.00"),
        high=Decimal("1510.00"),
        low=Decimal("1485.00"),
        close=Decimal("1495.00"),
        volume=50000,
        timestamp=ts,
    )
    d = tick.to_dict()
    restored = Tick.from_dict(d)
    assert restored.symbol == tick.symbol
    assert restored.ltp == tick.ltp
    assert restored.volume == tick.volume


def test_tick__frozen__immutable() -> None:
    ts = datetime(2026, 5, 28, 10, 30, 0, tzinfo=IST)
    tick = Tick(
        symbol="TCS",
        token="11536",
        ltp=Decimal("3500.00"),
        open=Decimal("3490.00"),
        high=Decimal("3510.00"),
        low=Decimal("3485.00"),
        close=Decimal("3495.00"),
        volume=20000,
        timestamp=ts,
    )
    try:
        tick.ltp = Decimal("9999")  # type: ignore[misc]
        assert False, "Should have raised FrozenInstanceError"
    except AttributeError:
        pass
