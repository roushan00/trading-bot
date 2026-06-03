from datetime import datetime
from decimal import Decimal

import pytest

from config.constants import IST
from risk_manager.position_sizer import (
    DuplicatePositionGuard,
    MaxPositionCapCheck,
    calculate_position_size,
)
from strategy_engine.signal import Direction, Signal


def _make_signal(direction: Direction = Direction.BUY, price: str = "2500") -> Signal:
    return Signal(
        strategy_name="test",
        symbol="RELIANCE",
        direction=direction,
        price=Decimal(price),
        timestamp=datetime(2026, 5, 28, 10, 0, 0, tzinfo=IST),
    )


# --- Position Sizer ---

def test_position_size__standard_calculation() -> None:
    # Portfolio 1L, risk 1%, stop 10 → qty = 100
    qty = calculate_position_size(
        portfolio_value=Decimal("100000"),
        risk_pct=Decimal("1"),
        entry_price=Decimal("1000"),
        stop_loss=Decimal("990"),
    )
    assert qty == 100


def test_position_size__tight_stop__small_qty() -> None:
    qty = calculate_position_size(
        portfolio_value=Decimal("100000"),
        risk_pct=Decimal("1"),
        entry_price=Decimal("1000"),
        stop_loss=Decimal("999"),
    )
    assert qty == 1000


def test_position_size__zero_stop_distance__returns_zero() -> None:
    qty = calculate_position_size(
        portfolio_value=Decimal("100000"),
        risk_pct=Decimal("1"),
        entry_price=Decimal("1000"),
        stop_loss=Decimal("1000"),
    )
    assert qty == 0


# --- Max Position Cap ---

@pytest.mark.asyncio
async def test_max_position__within_cap__passes() -> None:
    check = MaxPositionCapCheck(max_position_pct=Decimal("5"))
    context = {
        "portfolio_value": Decimal("100000"),
        "existing_position_value": Decimal("0"),
        "proposed_quantity": 2,
    }
    result = await check.check(_make_signal(price="2500"), context)
    assert result.passed is True


@pytest.mark.asyncio
async def test_max_position__exceeds_cap__blocks() -> None:
    check = MaxPositionCapCheck(max_position_pct=Decimal("5"))
    context = {
        "portfolio_value": Decimal("100000"),
        "existing_position_value": Decimal("4000"),
        "proposed_quantity": 1,
    }
    # 4000 + 2500*1 = 6500 = 6.5% > 5%
    result = await check.check(_make_signal(price="2500"), context)
    assert result.passed is False


@pytest.mark.asyncio
async def test_max_position__5pct_held__new_buy_blocked() -> None:
    check = MaxPositionCapCheck(max_position_pct=Decimal("5"))
    context = {
        "portfolio_value": Decimal("100000"),
        "existing_position_value": Decimal("5000"),
        "proposed_quantity": 1,
    }
    result = await check.check(_make_signal(price="2500"), context)
    assert result.passed is False


# --- Duplicate Position Guard ---

@pytest.mark.asyncio
async def test_duplicate__no_position__passes() -> None:
    check = DuplicatePositionGuard()
    result = await check.check(_make_signal(Direction.BUY), {"current_position_qty": 0})
    assert result.passed is True


@pytest.mark.asyncio
async def test_duplicate__already_long__buy_blocked() -> None:
    check = DuplicatePositionGuard()
    result = await check.check(_make_signal(Direction.BUY), {"current_position_qty": 10})
    assert result.passed is False
    assert "Already long" in result.reason


@pytest.mark.asyncio
async def test_duplicate__already_short__sell_blocked() -> None:
    check = DuplicatePositionGuard()
    result = await check.check(_make_signal(Direction.SELL), {"current_position_qty": -5})
    assert result.passed is False
    assert "Already short" in result.reason


@pytest.mark.asyncio
async def test_duplicate__long_position__sell_allowed() -> None:
    check = DuplicatePositionGuard()
    result = await check.check(_make_signal(Direction.SELL), {"current_position_qty": 10})
    assert result.passed is True
