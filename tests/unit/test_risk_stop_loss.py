from datetime import datetime
from decimal import Decimal

from config.constants import IST
from risk_manager.stop_loss import StopLossEngine
from strategy_engine.signal import Direction


def test_stop_loss__long_position__triggers_on_drop() -> None:
    engine = StopLossEngine()
    engine.register_stop("RELIANCE", Direction.BUY, Decimal("2400"), 10)
    ts = datetime(2026, 5, 28, 10, 0, 0, tzinfo=IST)

    signal = engine.check_price("RELIANCE", Decimal("2399"), ts)
    assert signal is not None
    assert signal.direction == Direction.SELL
    assert signal.symbol == "RELIANCE"


def test_stop_loss__long_position__no_trigger_above_stop() -> None:
    engine = StopLossEngine()
    engine.register_stop("RELIANCE", Direction.BUY, Decimal("2400"), 10)
    ts = datetime(2026, 5, 28, 10, 0, 0, tzinfo=IST)

    signal = engine.check_price("RELIANCE", Decimal("2450"), ts)
    assert signal is None


def test_stop_loss__short_position__triggers_on_rise() -> None:
    engine = StopLossEngine()
    engine.register_stop("INFY", Direction.SELL, Decimal("1500"), 5)
    ts = datetime(2026, 5, 28, 10, 0, 0, tzinfo=IST)

    signal = engine.check_price("INFY", Decimal("1501"), ts)
    assert signal is not None
    assert signal.direction == Direction.BUY


def test_stop_loss__triggers_once__then_removed() -> None:
    engine = StopLossEngine()
    engine.register_stop("TCS", Direction.BUY, Decimal("3400"), 10)
    ts = datetime(2026, 5, 28, 10, 0, 0, tzinfo=IST)

    signal1 = engine.check_price("TCS", Decimal("3399"), ts)
    assert signal1 is not None

    signal2 = engine.check_price("TCS", Decimal("3300"), ts)
    assert signal2 is None


def test_stop_loss__no_stop_registered__returns_none() -> None:
    engine = StopLossEngine()
    ts = datetime(2026, 5, 28, 10, 0, 0, tzinfo=IST)
    assert engine.check_price("RELIANCE", Decimal("2500"), ts) is None


def test_stop_loss__remove_stop__no_trigger() -> None:
    engine = StopLossEngine()
    engine.register_stop("RELIANCE", Direction.BUY, Decimal("2400"), 10)
    engine.remove_stop("RELIANCE")
    ts = datetime(2026, 5, 28, 10, 0, 0, tzinfo=IST)
    assert engine.check_price("RELIANCE", Decimal("2300"), ts) is None


def test_stop_loss__clear_all() -> None:
    engine = StopLossEngine()
    engine.register_stop("A", Direction.BUY, Decimal("100"), 10)
    engine.register_stop("B", Direction.SELL, Decimal("200"), 5)
    engine.clear_all()
    assert engine.get_active_stops() == {}


def test_stop_loss__at_exact_stop_price__triggers() -> None:
    engine = StopLossEngine()
    engine.register_stop("RELIANCE", Direction.BUY, Decimal("2400"), 10)
    ts = datetime(2026, 5, 28, 10, 0, 0, tzinfo=IST)

    signal = engine.check_price("RELIANCE", Decimal("2400"), ts)
    assert signal is not None
    assert signal.direction == Direction.SELL
