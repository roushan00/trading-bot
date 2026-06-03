from datetime import datetime
from decimal import Decimal

import pytest

from config.constants import IST
from risk_manager.pnl_guard import DailyPnLGuard, MaxDrawdownGuard
from strategy_engine.signal import Direction, Signal


def _make_signal() -> Signal:
    return Signal(
        strategy_name="test",
        symbol="RELIANCE",
        direction=Direction.BUY,
        price=Decimal("2500"),
        timestamp=datetime(2026, 5, 28, 10, 0, 0, tzinfo=IST),
    )


@pytest.mark.asyncio
async def test_daily_pnl__within_limit__passes() -> None:
    guard = DailyPnLGuard(max_loss_pct=Decimal("2.0"))
    result = await guard.check(_make_signal(), {"daily_pnl_pct": Decimal("-1.5")})
    assert result.passed is True


@pytest.mark.asyncio
async def test_daily_pnl__at_limit__blocks() -> None:
    guard = DailyPnLGuard(max_loss_pct=Decimal("2.0"))
    result = await guard.check(_make_signal(), {"daily_pnl_pct": Decimal("-2.0")})
    assert result.passed is False


@pytest.mark.asyncio
async def test_daily_pnl__exceeds_limit__blocks() -> None:
    guard = DailyPnLGuard(max_loss_pct=Decimal("2.0"))
    result = await guard.check(_make_signal(), {"daily_pnl_pct": Decimal("-2.1")})
    assert result.passed is False


@pytest.mark.asyncio
async def test_daily_pnl__positive_pnl__passes() -> None:
    guard = DailyPnLGuard(max_loss_pct=Decimal("2.0"))
    result = await guard.check(_make_signal(), {"daily_pnl_pct": Decimal("5.0")})
    assert result.passed is True


@pytest.mark.asyncio
async def test_drawdown__within_limit__passes() -> None:
    guard = MaxDrawdownGuard(max_drawdown_pct=Decimal("10.0"))
    result = await guard.check(_make_signal(), {"current_drawdown_pct": Decimal("8.0")})
    assert result.passed is True


@pytest.mark.asyncio
async def test_drawdown__at_limit__blocks() -> None:
    guard = MaxDrawdownGuard(max_drawdown_pct=Decimal("10.0"))
    result = await guard.check(_make_signal(), {"current_drawdown_pct": Decimal("10.0")})
    assert result.passed is False


@pytest.mark.asyncio
async def test_drawdown__exceeds_limit__triggers_kill_switch() -> None:
    callback_called = {}

    async def mock_kill(triggered_by: str, reason: str) -> None:
        callback_called["triggered_by"] = triggered_by
        callback_called["reason"] = reason

    guard = MaxDrawdownGuard(max_drawdown_pct=Decimal("10.0"))
    guard.set_kill_switch_callback(mock_kill)
    result = await guard.check(_make_signal(), {"current_drawdown_pct": Decimal("10.5")})
    assert result.passed is False
    assert callback_called["triggered_by"] == "max_drawdown_guard"
