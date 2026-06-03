import json
from datetime import datetime

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from config.constants import IST
from pii_masking.masker import mask_event_data

logger = structlog.get_logger(__name__)


class AuditLogger:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def log(self, event_type: str, event_data: dict) -> None:
        masked = mask_event_data(event_data)
        data_json = json.dumps(masked, default=str)

        async with self._session_factory() as session:
            await session.execute(
                text("""
                    INSERT INTO audit_log (event_type, event_data, timestamp)
                    VALUES (:event_type, :event_data, :timestamp)
                """),
                {
                    "event_type": event_type,
                    "event_data": data_json,
                    "timestamp": datetime.now(tz=IST),
                },
            )
            await session.commit()

        logger.info("audit_event_logged", event_type=event_type)

    async def log_signal(self, signal_data: dict) -> None:
        await self.log("SIGNAL", signal_data)

    async def log_order(self, order_data: dict) -> None:
        await self.log("ORDER", order_data)

    async def log_fill(self, fill_data: dict) -> None:
        await self.log("FILL", fill_data)

    async def log_kill_switch(self, ks_data: dict) -> None:
        await self.log("KILL_SWITCH", ks_data)
