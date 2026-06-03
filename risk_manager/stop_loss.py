from decimal import Decimal

import structlog

from config.constants import IST
from strategy_engine.signal import Direction, Signal

logger = structlog.get_logger(__name__)


class StopLossEngine:
    def __init__(self) -> None:
        self._stops: dict[str, dict] = {}

    def register_stop(self, symbol: str, direction: Direction, stop_price: Decimal, quantity: int) -> None:
        self._stops[symbol] = {
            "direction": direction,
            "stop_price": stop_price,
            "quantity": quantity,
        }
        logger.info(
            "stop_loss_registered",
            symbol=symbol,
            direction=direction.value,
            stop_price=str(stop_price),
            quantity=quantity,
        )

    def remove_stop(self, symbol: str) -> None:
        self._stops.pop(symbol, None)
        logger.info("stop_loss_removed", symbol=symbol)

    def check_price(self, symbol: str, current_price: Decimal, timestamp) -> Signal | None:
        stop = self._stops.get(symbol)
        if stop is None:
            return None

        triggered = False

        if stop["direction"] == Direction.BUY and current_price <= stop["stop_price"]:
            triggered = True
        elif stop["direction"] == Direction.SELL and current_price >= stop["stop_price"]:
            triggered = True

        if triggered:
            exit_direction = Direction.SELL if stop["direction"] == Direction.BUY else Direction.BUY
            logger.warning(
                "stop_loss_triggered",
                symbol=symbol,
                direction=stop["direction"].value,
                stop_price=str(stop["stop_price"]),
                current_price=str(current_price),
            )
            self._stops.pop(symbol)
            return Signal(
                strategy_name="stop_loss",
                symbol=symbol,
                direction=exit_direction,
                price=current_price,
                timestamp=timestamp,
                metadata={
                    "trigger": "stop_loss",
                    "stop_price": str(stop["stop_price"]),
                },
            )

        return None

    def get_active_stops(self) -> dict[str, dict]:
        return dict(self._stops)

    def clear_all(self) -> None:
        self._stops.clear()
        logger.info("all_stop_losses_cleared")
