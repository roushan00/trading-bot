from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from config.constants import IST


@dataclass(frozen=True, slots=True)
class Tick:
    symbol: str
    token: str
    ltp: Decimal
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    timestamp: datetime

    @staticmethod
    def _ensure_ist(dt: datetime) -> datetime:
        if dt.tzinfo is None:
            return dt.replace(tzinfo=IST)
        return dt

    @classmethod
    def from_smartapi(cls, raw: dict) -> "Tick":
        return cls(
            symbol=raw.get("name", raw.get("symbolName", "")),
            token=str(raw.get("token", "")),
            ltp=Decimal(str(raw.get("last_traded_price", raw.get("ltp", 0)) / 100)),
            open=Decimal(str(raw.get("open_price_of_the_day", raw.get("open", 0)) / 100)),
            high=Decimal(str(raw.get("high_price_of_the_day", raw.get("high", 0)) / 100)),
            low=Decimal(str(raw.get("low_price_of_the_day", raw.get("low", 0)) / 100)),
            close=Decimal(str(raw.get("closed_price", raw.get("close", 0)) / 100)),
            volume=int(raw.get("volume_trade_for_the_day", raw.get("volume", 0))),
            timestamp=datetime.now(tz=IST),
        )

    @classmethod
    def from_dict(cls, data: dict) -> "Tick":
        return cls(
            symbol=data["symbol"],
            token=data.get("token", ""),
            ltp=Decimal(str(data["ltp"])),
            open=Decimal(str(data["open"])),
            high=Decimal(str(data["high"])),
            low=Decimal(str(data["low"])),
            close=Decimal(str(data["close"])),
            volume=int(data["volume"]),
            timestamp=cls._ensure_ist(
                datetime.fromisoformat(data["timestamp"]) if isinstance(data["timestamp"], str) else data["timestamp"]
            ),
        )

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "token": self.token,
            "ltp": str(self.ltp),
            "open": str(self.open),
            "high": str(self.high),
            "low": str(self.low),
            "close": str(self.close),
            "volume": self.volume,
            "timestamp": self.timestamp.isoformat(),
        }
