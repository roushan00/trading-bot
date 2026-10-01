import json
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum

from config.constants import IST


class Direction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass(frozen=True, slots=True)
class Signal:
    strategy_name: str
    symbol: str
    direction: Direction
    price: Decimal
    timestamp: datetime
    stop_loss: Decimal | None = None
    take_profit: Decimal | None = None
    metadata: dict = field(default_factory=dict)

    @staticmethod
    def _ensure_ist(dt: datetime) -> datetime:
        if dt.tzinfo is None:
            return dt.replace(tzinfo=IST)
        return dt

    def to_json(self) -> str:
        return json.dumps({
            "strategy_name": self.strategy_name,
            "symbol": self.symbol,
            "direction": self.direction.value,
            "price": str(self.price),
            "timestamp": self.timestamp.isoformat(),
            "stop_loss": str(self.stop_loss) if self.stop_loss else None,
            "take_profit": str(self.take_profit) if self.take_profit else None,
            "metadata": self.metadata,
        })

    @classmethod
    def from_json(cls, raw: str) -> "Signal":
        d = json.loads(raw)
        return cls(
            strategy_name=d["strategy_name"],
            symbol=d["symbol"],
            direction=Direction(d["direction"]),
            price=Decimal(d["price"]),
            timestamp=cls._ensure_ist(datetime.fromisoformat(d["timestamp"])),
            stop_loss=Decimal(d["stop_loss"]) if d.get("stop_loss") else None,
            take_profit=Decimal(d["take_profit"]) if d.get("take_profit") else None,
            metadata=d.get("metadata", {}),
        )
