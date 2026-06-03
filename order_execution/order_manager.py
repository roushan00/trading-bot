from datetime import datetime
from decimal import Decimal
from enum import Enum

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from config.constants import IST
from config.settings import settings
from order_execution.brokers.base_broker import BaseBroker
from risk_manager.risk_engine import RiskEngine
from strategy_engine.signal import Signal

logger = structlog.get_logger(__name__)


class OrderState(str, Enum):
    CREATED = "CREATED"
    VALIDATED = "VALIDATED"
    OPEN = "OPEN"
    COMPLETE = "COMPLETE"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class OrderManager:
    def __init__(
        self,
        broker: BaseBroker,
        risk_engine: RiskEngine,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._broker = broker
        self._risk_engine = risk_engine
        self._session_factory = session_factory

    async def _log_audit(self, session: AsyncSession, event_type: str, event_data: str) -> None:
        await session.execute(
            text("""
                INSERT INTO audit_log (event_type, event_data, timestamp)
                VALUES (:event_type, :event_data, :timestamp)
            """),
            {
                "event_type": event_type,
                "event_data": event_data,
                "timestamp": datetime.now(tz=IST),
            },
        )

    async def _create_order(self, session: AsyncSession, signal: Signal, quantity: int) -> int:
        now = datetime.now(tz=IST)
        result = await session.execute(
            text("""
                INSERT INTO orders (signal_id, symbol, direction, quantity, price, status, created_at, updated_at)
                VALUES (0, :symbol, :direction, :quantity, :price, :status, :created_at, :updated_at)
                RETURNING id
            """),
            {
                "symbol": signal.symbol,
                "direction": signal.direction.value,
                "quantity": quantity,
                "price": signal.price,
                "status": OrderState.CREATED.value,
                "created_at": now,
                "updated_at": now,
            },
        )
        order_id = result.scalar_one()
        await self._log_audit(
            session,
            "ORDER_CREATED",
            f'{{"order_id": {order_id}, "symbol": "{signal.symbol}", "direction": "{signal.direction.value}", "quantity": {quantity}, "price": "{signal.price}"}}',
        )
        return order_id

    async def _update_order_status(
        self,
        session: AsyncSession,
        order_id: int,
        status: OrderState,
        fill_price: Decimal | None = None,
        broker_order_id: str | None = None,
    ) -> None:
        now = datetime.now(tz=IST)
        params: dict = {
            "status": status.value,
            "updated_at": now,
            "order_id": order_id,
        }
        set_clauses = ["status = :status", "updated_at = :updated_at"]
        if fill_price is not None:
            set_clauses.append("fill_price = :fill_price")
            params["fill_price"] = fill_price
        if broker_order_id is not None:
            set_clauses.append("broker_order_id = :broker_order_id")
            params["broker_order_id"] = broker_order_id

        await session.execute(
            text(f"UPDATE orders SET {', '.join(set_clauses)} WHERE id = :order_id"),
            params,
        )
        await self._log_audit(
            session,
            f"ORDER_{status.value}",
            f'{{"order_id": {order_id}, "status": "{status.value}"}}',
        )

    async def process_signal(self, signal: Signal, context: dict) -> dict:
        if not settings.PAPER_TRADING_MODE:
            logger.critical("live_trading_blocked", reason="v1.0 is paper only")
            return {"status": "REJECTED", "reason": "Live trading disabled in v1.0"}

        async with self._session_factory() as session:
            quantity = context.get("quantity", 1)
            order_id = await self._create_order(session, signal, quantity)
            await session.commit()

            # Validate through risk engine
            passed, results = await self._risk_engine.validate(signal, context)

            if not passed:
                failed_check = next((r for r in results if not r.passed), None)
                reason = failed_check.reason if failed_check else "Unknown"
                await self._update_order_status(session, order_id, OrderState.REJECTED)
                await session.commit()
                logger.warning("order_rejected", order_id=order_id, reason=reason)
                return {"status": "REJECTED", "order_id": order_id, "reason": reason}

            await self._update_order_status(session, order_id, OrderState.VALIDATED)
            await session.commit()

            # Send to broker
            try:
                await self._update_order_status(session, order_id, OrderState.OPEN)
                await session.commit()

                fill = await self._broker.place_order(
                    symbol=signal.symbol,
                    direction=signal.direction.value,
                    quantity=quantity,
                    price=signal.price,
                    order_id=order_id,
                )

                await self._update_order_status(
                    session,
                    order_id,
                    OrderState.COMPLETE,
                    fill_price=fill.get("fill_price"),
                    broker_order_id=fill.get("broker_order_id"),
                )
                await session.commit()

                logger.info(
                    "order_complete",
                    order_id=order_id,
                    symbol=signal.symbol,
                    fill_price=str(fill.get("fill_price")),
                )

                return {
                    "status": "COMPLETE",
                    "order_id": order_id,
                    "fill": fill,
                }

            except Exception:
                logger.error("order_execution_error", order_id=order_id, exc_info=True)
                await self._update_order_status(session, order_id, OrderState.REJECTED)
                await session.commit()
                return {"status": "REJECTED", "order_id": order_id, "reason": "Broker error"}
