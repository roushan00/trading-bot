from datetime import datetime
from decimal import Decimal

from config.constants import IST
from data_ingestion.candle_builder import CandleBuilder
from data_ingestion.normalizer import Tick


def _make_tick(symbol: str, ltp: str, minute: int, second: int = 0, volume: int = 100) -> Tick:
    return Tick(
        symbol=symbol,
        token="1234",
        ltp=Decimal(ltp),
        open=Decimal(ltp),
        high=Decimal(ltp),
        low=Decimal(ltp),
        close=Decimal(ltp),
        volume=volume,
        timestamp=datetime(2026, 5, 28, 10, minute, second, tzinfo=IST),
    )


def test_candle_builder__single_period__no_complete_until_next() -> None:
    builder = CandleBuilder(timeframes=["1min"])
    t1 = _make_tick("RELIANCE", "100.00", 0, 10)
    t2 = _make_tick("RELIANCE", "101.00", 0, 30)
    assert builder.on_tick(t1) == []
    assert builder.on_tick(t2) == []


def test_candle_builder__period_rollover__emits_candle() -> None:
    builder = CandleBuilder(timeframes=["1min"])
    t1 = _make_tick("RELIANCE", "100.00", 0, 10, volume=50)
    t2 = _make_tick("RELIANCE", "102.00", 0, 30, volume=70)
    t3 = _make_tick("RELIANCE", "103.00", 1, 5, volume=30)

    builder.on_tick(t1)
    builder.on_tick(t2)
    candles = builder.on_tick(t3)

    assert len(candles) == 1
    c = candles[0]
    assert c.symbol == "RELIANCE"
    assert c.timeframe == "1min"
    assert c.open == Decimal("100.00")
    assert c.high == Decimal("102.00")
    assert c.low == Decimal("100.00")
    assert c.close == Decimal("102.00")
    assert c.volume == 120


def test_candle_builder__ohlcv_correctness__100_ticks() -> None:
    builder = CandleBuilder(timeframes=["1min"])
    ticks = []
    prices = [Decimal("100")] + [Decimal(str(100 + i * 0.5)) for i in range(1, 50)] + \
             [Decimal(str(124.5 - i * 0.5)) for i in range(50)]

    completed_candles: list = []
    for i, price in enumerate(prices):
        second = i % 60
        minute = i // 60
        t = Tick(
            symbol="TEST",
            token="9999",
            ltp=price,
            open=price,
            high=price,
            low=price,
            close=price,
            volume=10,
            timestamp=datetime(2026, 5, 28, 10, minute, second, tzinfo=IST),
        )
        completed_candles.extend(builder.on_tick(t))

    flushed = builder.flush_all()
    # on_tick already emitted completed candles; flush returns the remaining partial
    # Collect all candles: completed during ticks + flushed
    all_candles = completed_candles + flushed
    assert len(all_candles) >= 1
    sorted_candles = sorted(all_candles, key=lambda c: c.timestamp)
    assert sorted_candles[0].open == Decimal("100")
    total_volume = sum(c.volume for c in all_candles)
    assert total_volume == 10 * len(prices)


def test_candle_builder__5min_timeframe__groups_correctly() -> None:
    builder = CandleBuilder(timeframes=["5min"])
    builder.on_tick(_make_tick("INFY", "100", 0))
    builder.on_tick(_make_tick("INFY", "105", 2))
    builder.on_tick(_make_tick("INFY", "103", 4))
    candles = builder.on_tick(_make_tick("INFY", "110", 5))

    assert len(candles) == 1
    c = candles[0]
    assert c.timeframe == "5min"
    assert c.open == Decimal("100")
    assert c.high == Decimal("105")
    assert c.close == Decimal("103")


def test_candle_builder__multiple_symbols__independent() -> None:
    builder = CandleBuilder(timeframes=["1min"])
    builder.on_tick(_make_tick("RELIANCE", "100", 0))
    builder.on_tick(_make_tick("INFY", "200", 0))
    builder.on_tick(_make_tick("RELIANCE", "101", 0, 30))
    builder.on_tick(_make_tick("INFY", "199", 0, 30))

    candles = builder.flush_all()
    symbols = {c.symbol for c in candles}
    assert symbols == {"RELIANCE", "INFY"}


def test_candle_builder__flush__returns_partial_candles() -> None:
    builder = CandleBuilder(timeframes=["1min"])
    builder.on_tick(_make_tick("TCS", "3500", 0))
    builder.on_tick(_make_tick("TCS", "3510", 0, 30))

    candles = builder.flush_all()
    assert len(candles) == 1
    assert candles[0].open == Decimal("3500")
    assert candles[0].close == Decimal("3510")


def test_candle_builder__callback__fires_on_complete() -> None:
    received: list = []
    builder = CandleBuilder(timeframes=["1min"], on_candle=lambda c: received.append(c))

    builder.on_tick(_make_tick("X", "10", 0))
    builder.on_tick(_make_tick("X", "11", 1))

    assert len(received) == 1
    assert received[0].symbol == "X"
