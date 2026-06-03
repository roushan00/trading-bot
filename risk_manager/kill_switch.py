import json
from datetime import datetime

import redis.asyncio as redis
import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from config.constants import IST
from config.settings import settings
from risk_manager.risk_engine import RiskCheck, RiskCheckResult
from strategy_engine.signal import Signal

logger = structlog.get_logger(__name__)

KILL_SWITCH_KEY = "TRADING_HALTED"


class KillSwitchCheck(RiskCheck):
    name = "kill_switch"

    def __init__(self, redis_client: redis.Redis) -> None:
        self._redis = redis_client

    async def check(self, signal: Signal, context: dict) -> RiskCheckResult:
        halted = await self._redis.get(KILL_SWITCH_KEY)
        if halted and halted == "1":
            return RiskCheckResult(
                passed=False,
                check_name=self.name,
                reason="Trading is halted — kill switch active",
            )
        return RiskCheckResult(passed=True, check_name=self.name)


class KillSwitch:
    def __init__(
        self,
        redis_client: redis.Redis,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._redis = redis_client
        self._session_factory = session_factory

    async def activate(self, triggered_by: str, reason: str) -> None:
        await self._redis.set(KILL_SWITCH_KEY, "1")

        async with self._session_factory() as session:
            await session.execute(
                text("""
                    INSERT INTO kill_switch_events (triggered_by, reason, timestamp)
                    VALUES (:triggered_by, :reason, :timestamp)
                """),
                {
                    "triggered_by": triggered_by,
                    "reason": reason,
                    "timestamp": datetime.now(tz=IST),
                },
            )
            await session.commit()

        logger.critical(
            "kill_switch_activated",
            triggered_by=triggered_by,
            reason=reason,
        )

    async def deactivate(self) -> None:
        await self._redis.delete(KILL_SWITCH_KEY)
        logger.info("kill_switch_deactivated")

    async def is_active(self) -> bool:
        val = await self._redis.get(KILL_SWITCH_KEY)
        return val is not None and val == "1"
