from dataclasses import dataclass

import structlog

from strategy_engine.signal import Signal

logger = structlog.get_logger(__name__)


@dataclass
class RiskCheckResult:
    passed: bool
    check_name: str
    reason: str = ""


class RiskCheck:
    name: str = "base_check"

    async def check(self, signal: Signal, context: dict) -> RiskCheckResult:
        raise NotImplementedError


class RiskEngine:
    def __init__(self, checks: list[RiskCheck]) -> None:
        self._checks = checks

    async def validate(self, signal: Signal, context: dict) -> tuple[bool, list[RiskCheckResult]]:
        results: list[RiskCheckResult] = []

        for check in self._checks:
            try:
                result = await check.check(signal, context)
            except Exception:
                logger.error("risk_check_exception", check=check.name, exc_info=True)
                result = RiskCheckResult(
                    passed=False,
                    check_name=check.name,
                    reason="Exception during check",
                )

            results.append(result)

            if not result.passed:
                logger.warning(
                    "risk_check_failed",
                    check=result.check_name,
                    reason=result.reason,
                    symbol=signal.symbol,
                    direction=signal.direction.value,
                )
                return False, results

            logger.debug(
                "risk_check_passed",
                check=result.check_name,
                symbol=signal.symbol,
            )

        logger.info(
            "risk_validation_passed",
            symbol=signal.symbol,
            direction=signal.direction.value,
            checks_passed=len(results),
        )
        return True, results
