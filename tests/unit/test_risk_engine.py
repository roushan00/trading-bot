from datetime import datetime
from decimal import Decimal

import pytest

from config.constants import IST
from risk_manager.risk_engine import RiskCheck, RiskCheckResult, RiskEngine
from strategy_engine.signal import Direction, Signal


def _make_signal(direction: Direction = Direction.BUY, symbol: str = "RELIANCE", price: str = "2500") -> Signal:
    return Signal(
        strategy_name="test",
        symbol=symbol,
        direction=direction,
        price=Decimal(price),
        timestamp=datetime(2026, 5, 28, 10, 0, 0, tzinfo=IST),
    )


class AlwaysPassCheck(RiskCheck):
    name = "always_pass"

    async def check(self, signal: Signal, context: dict) -> RiskCheckResult:
        return RiskCheckResult(passed=True, check_name=self.name)


class AlwaysFailCheck(RiskCheck):
    name = "always_fail"

    async def check(self, signal: Signal, context: dict) -> RiskCheckResult:
        return RiskCheckResult(passed=False, check_name=self.name, reason="blocked")


class ExplodingCheck(RiskCheck):
    name = "exploding"

    async def check(self, signal: Signal, context: dict) -> RiskCheckResult:
        raise RuntimeError("boom")


@pytest.mark.asyncio
async def test_risk_engine__all_pass__returns_true() -> None:
    engine = RiskEngine([AlwaysPassCheck(), AlwaysPassCheck()])
    passed, results = await engine.validate(_make_signal(), {})
    assert passed is True
    assert len(results) == 2
    assert all(r.passed for r in results)


@pytest.mark.asyncio
async def test_risk_engine__first_fails__short_circuits() -> None:
    engine = RiskEngine([AlwaysFailCheck(), AlwaysPassCheck()])
    passed, results = await engine.validate(_make_signal(), {})
    assert passed is False
    assert len(results) == 1
    assert results[0].check_name == "always_fail"


@pytest.mark.asyncio
async def test_risk_engine__second_fails__first_passes() -> None:
    engine = RiskEngine([AlwaysPassCheck(), AlwaysFailCheck()])
    passed, results = await engine.validate(_make_signal(), {})
    assert passed is False
    assert len(results) == 2
    assert results[0].passed is True
    assert results[1].passed is False


@pytest.mark.asyncio
async def test_risk_engine__exception__treated_as_failure() -> None:
    engine = RiskEngine([ExplodingCheck()])
    passed, results = await engine.validate(_make_signal(), {})
    assert passed is False
    assert results[0].reason == "Exception during check"


@pytest.mark.asyncio
async def test_risk_engine__empty_checks__passes() -> None:
    engine = RiskEngine([])
    passed, results = await engine.validate(_make_signal(), {})
    assert passed is True
    assert len(results) == 0
