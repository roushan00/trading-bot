from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from config.constants import IST
from risk_manager.kill_switch import KILL_SWITCH_KEY, KillSwitchCheck
from risk_manager.risk_engine import RiskCheckResult
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
async def test_kill_switch__not_set__passes() -> None:
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    check = KillSwitchCheck(mock_redis)
    result = await check.check(_make_signal(), {})
    assert result.passed is True


@pytest.mark.asyncio
async def test_kill_switch__set_to_1__blocks() -> None:
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value="1")
    check = KillSwitchCheck(mock_redis)
    result = await check.check(_make_signal(), {})
    assert result.passed is False
    assert "halted" in result.reason.lower()


@pytest.mark.asyncio
async def test_kill_switch__set_to_0__passes() -> None:
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value="0")
    check = KillSwitchCheck(mock_redis)
    result = await check.check(_make_signal(), {})
    assert result.passed is True
