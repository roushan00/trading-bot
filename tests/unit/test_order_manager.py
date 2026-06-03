from contextlib import asynccontextmanager
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from config.constants import IST
from order_execution.brokers.paper_broker import PaperBroker
from order_execution.order_manager import OrderManager
from risk_manager.risk_engine import RiskCheckResult, RiskEngine
from strategy_engine.signal import Direction, Signal


def _make_signal() -> Signal:
    return Signal(
        strategy_name="ema_crossover",
        symbol="RELIANCE",
        direction=Direction.BUY,
        price=Decimal("2500"),
        timestamp=datetime(2026, 5, 28, 10, 0, 0, tzinfo=IST),
        stop_loss=Decimal("2450"),
    )


class AlwaysPassEngine(RiskEngine):
    def __init__(self) -> None:
        super().__init__([])

    async def validate(self, signal, context):
        return True, [RiskCheckResult(passed=True, check_name="mock")]


class AlwaysFailEngine(RiskEngine):
    def __init__(self) -> None:
        super().__init__([])

    async def validate(self, signal, context):
        return False, [RiskCheckResult(passed=False, check_name="mock", reason="blocked")]


def _make_mock_session_factory():
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one=lambda: 1))
    mock_session.commit = AsyncMock()

    class FakeFactory:
        def __call__(self):
            return self

        async def __aenter__(self):
            return mock_session

        async def __aexit__(self, *args):
            pass

    return FakeFactory()


@pytest.mark.asyncio
async def test_order_manager__end_to_end__complete() -> None:
    broker = PaperBroker()
    risk = AlwaysPassEngine()
    factory = _make_mock_session_factory()

    manager = OrderManager(broker, risk, factory)
    result = await manager.process_signal(_make_signal(), {"quantity": 5})

    assert result["status"] == "COMPLETE"
    assert result["order_id"] == 1
    assert "fill" in result


@pytest.mark.asyncio
async def test_order_manager__risk_rejected__no_broker_call() -> None:
    broker = PaperBroker()
    risk = AlwaysFailEngine()
    factory = _make_mock_session_factory()

    manager = OrderManager(broker, risk, factory)
    result = await manager.process_signal(_make_signal(), {"quantity": 5})

    assert result["status"] == "REJECTED"
    assert "blocked" in result["reason"]


@pytest.mark.asyncio
async def test_order_manager__live_mode_blocked() -> None:
    broker = PaperBroker()
    risk = AlwaysPassEngine()
    factory = _make_mock_session_factory()

    manager = OrderManager(broker, risk, factory)

    with patch("order_execution.order_manager.settings") as mock_settings:
        mock_settings.PAPER_TRADING_MODE = False
        result = await manager.process_signal(_make_signal(), {"quantity": 1})

    assert result["status"] == "REJECTED"
    assert "v1.0" in result["reason"]
