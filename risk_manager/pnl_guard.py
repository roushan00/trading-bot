from decimal import Decimal

import structlog

from config.settings import settings
from risk_manager.risk_engine import RiskCheck, RiskCheckResult
from strategy_engine.signal import Signal

logger = structlog.get_logger(__name__)


class DailyPnLGuard(RiskCheck):
    name = "daily_pnl_guard"

    def __init__(self, max_loss_pct: Decimal | None = None) -> None:
        self._max_loss_pct = max_loss_pct or settings.MAX_DAILY_LOSS_PCT

    async def check(self, signal: Signal, context: dict) -> RiskCheckResult:
        daily_pnl_pct = context.get("daily_pnl_pct", Decimal("0"))

        if daily_pnl_pct <= -self._max_loss_pct:
            return RiskCheckResult(
                passed=False,
                check_name=self.name,
                reason=f"Daily loss {daily_pnl_pct}% exceeds limit -{self._max_loss_pct}%",
            )

        return RiskCheckResult(passed=True, check_name=self.name)


class MaxDrawdownGuard(RiskCheck):
    name = "max_drawdown_guard"

    def __init__(self, max_drawdown_pct: Decimal | None = None) -> None:
        self._max_drawdown_pct = max_drawdown_pct or settings.MAX_DRAWDOWN_PCT
        self._kill_switch_callback = None

    def set_kill_switch_callback(self, callback) -> None:
        self._kill_switch_callback = callback

    async def check(self, signal: Signal, context: dict) -> RiskCheckResult:
        current_drawdown_pct = context.get("current_drawdown_pct", Decimal("0"))

        if current_drawdown_pct >= self._max_drawdown_pct:
            if self._kill_switch_callback:
                await self._kill_switch_callback(
                    triggered_by="max_drawdown_guard",
                    reason=f"Drawdown {current_drawdown_pct}% exceeds limit {self._max_drawdown_pct}%",
                )

            return RiskCheckResult(
                passed=False,
                check_name=self.name,
                reason=f"Drawdown {current_drawdown_pct}% exceeds limit {self._max_drawdown_pct}%",
            )

        return RiskCheckResult(passed=True, check_name=self.name)
