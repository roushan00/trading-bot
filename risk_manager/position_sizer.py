from decimal import Decimal

import structlog

from config.settings import settings
from risk_manager.risk_engine import RiskCheck, RiskCheckResult
from strategy_engine.signal import Signal

logger = structlog.get_logger(__name__)


def calculate_position_size(
    portfolio_value: Decimal,
    risk_pct: Decimal,
    entry_price: Decimal,
    stop_loss: Decimal,
) -> int:
    if entry_price == stop_loss:
        return 0

    stop_distance = abs(entry_price - stop_loss)
    if stop_distance == Decimal("0"):
        return 0

    risk_amount = portfolio_value * (risk_pct / Decimal("100"))
    quantity = int(risk_amount / stop_distance)
    return max(quantity, 0)


class MaxPositionCapCheck(RiskCheck):
    name = "max_position_cap"

    def __init__(self, max_position_pct: Decimal | None = None) -> None:
        self._max_position_pct = max_position_pct or settings.MAX_POSITION_PCT

    async def check(self, signal: Signal, context: dict) -> RiskCheckResult:
        portfolio_value = context.get("portfolio_value", Decimal("0"))
        existing_position_value = context.get("existing_position_value", Decimal("0"))
        proposed_quantity = context.get("proposed_quantity", 0)

        if portfolio_value == Decimal("0"):
            return RiskCheckResult(
                passed=False,
                check_name=self.name,
                reason="Portfolio value is zero",
            )

        new_position_value = existing_position_value + (signal.price * proposed_quantity)
        position_pct = (new_position_value / portfolio_value) * Decimal("100")

        if position_pct > self._max_position_pct:
            return RiskCheckResult(
                passed=False,
                check_name=self.name,
                reason=f"Position {position_pct:.1f}% exceeds cap {self._max_position_pct}%",
            )

        return RiskCheckResult(passed=True, check_name=self.name)


class DuplicatePositionGuard(RiskCheck):
    name = "duplicate_position_guard"

    async def check(self, signal: Signal, context: dict) -> RiskCheckResult:
        current_position = context.get("current_position_qty", 0)

        from strategy_engine.signal import Direction

        if signal.direction == Direction.BUY and current_position > 0:
            return RiskCheckResult(
                passed=False,
                check_name=self.name,
                reason=f"Already long {signal.symbol} (qty={current_position})",
            )

        if signal.direction == Direction.SELL and current_position < 0:
            return RiskCheckResult(
                passed=False,
                check_name=self.name,
                reason=f"Already short {signal.symbol} (qty={current_position})",
            )

        return RiskCheckResult(passed=True, check_name=self.name)
