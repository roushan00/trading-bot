import uuid
from datetime import datetime
from decimal import Decimal

import structlog

from backtesting.commission import calculate_buy_cost, calculate_sell_proceeds
from config.constants import IST
from order_execution.brokers.base_broker import BaseBroker

logger = structlog.get_logger(__name__)


class PaperBroker(BaseBroker):
    def __init__(self, slippage_pct: Decimal = Decimal("0.05")) -> None:
        self._slippage_rate = slippage_pct / Decimal("100")
        self._orders: dict[str, dict] = {}
        self._positions: dict[str, dict] = {}

    async def place_order(
        self,
        symbol: str,
        direction: str,
        quantity: int,
        price: Decimal,
        order_id: int,
    ) -> dict:
        broker_order_id = f"PAPER-{uuid.uuid4().hex[:12].upper()}"

        if direction == "BUY":
            cost_info = calculate_buy_cost(price, quantity, self._slippage_rate)
            fill_price = cost_info["fill_price"]
        else:
            cost_info = calculate_sell_proceeds(price, quantity, self._slippage_rate)
            fill_price = cost_info["fill_price"]

        order_record = {
            "broker_order_id": broker_order_id,
            "order_id": order_id,
            "symbol": symbol,
            "direction": direction,
            "quantity": quantity,
            "requested_price": price,
            "fill_price": fill_price,
            "status": "COMPLETE",
            "filled_at": datetime.now(tz=IST),
        }
        self._orders[broker_order_id] = order_record

        pos = self._positions.get(symbol, {"symbol": symbol, "quantity": 0, "avg_price": Decimal("0")})
        if direction == "BUY":
            total_cost = pos["avg_price"] * pos["quantity"] + fill_price * quantity
            pos["quantity"] += quantity
            pos["avg_price"] = total_cost / pos["quantity"] if pos["quantity"] > 0 else Decimal("0")
        else:
            pos["quantity"] -= quantity

        if pos["quantity"] == 0:
            self._positions.pop(symbol, None)
        else:
            self._positions[symbol] = pos

        logger.info(
            "paper_order_filled",
            broker_order_id=broker_order_id,
            symbol=symbol,
            direction=direction,
            quantity=quantity,
            fill_price=str(fill_price),
        )

        return order_record

    async def cancel_order(self, broker_order_id: str) -> dict:
        order = self._orders.get(broker_order_id)
        if order and order["status"] != "COMPLETE":
            order["status"] = "CANCELLED"
            return order
        return {"error": "Order not found or already complete"}

    async def get_order_status(self, broker_order_id: str) -> dict:
        order = self._orders.get(broker_order_id)
        if order:
            return order
        return {"error": "Order not found", "status": "UNKNOWN"}

    async def get_positions(self) -> list[dict]:
        return list(self._positions.values())

    async def square_off_all(self) -> list[dict]:
        results = []
        for symbol, pos in list(self._positions.items()):
            if pos["quantity"] > 0:
                result = await self.place_order(
                    symbol=symbol,
                    direction="SELL",
                    quantity=pos["quantity"],
                    price=pos["avg_price"],
                    order_id=-1,
                )
                results.append(result)
            elif pos["quantity"] < 0:
                result = await self.place_order(
                    symbol=symbol,
                    direction="BUY",
                    quantity=abs(pos["quantity"]),
                    price=pos["avg_price"],
                    order_id=-1,
                )
                results.append(result)

        logger.info("paper_square_off_complete", closed_positions=len(results))
        return results
