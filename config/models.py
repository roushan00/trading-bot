import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    Enum,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from config.database import Base


class OrderStatus(str, enum.Enum):
    CREATED = "CREATED"
    VALIDATED = "VALIDATED"
    OPEN = "OPEN"
    COMPLETE = "COMPLETE"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class SignalDirection(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class OHLCV(Base):
    __tablename__ = "ohlcv"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    open: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    volume: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        Index("ix_ohlcv_symbol_timeframe_timestamp", "symbol", "timeframe", "timestamp", unique=True),
    )


class Signal(Base):
    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    strategy_name: Mapped[str] = mapped_column(String(100), nullable=False)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    direction: Mapped[SignalDirection] = mapped_column(Enum(SignalDirection), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    stop_loss: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    take_profit: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    signal_id: Mapped[int] = mapped_column(Integer, nullable=False)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    direction: Mapped[SignalDirection] = mapped_column(Enum(SignalDirection), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    fill_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), nullable=False, default=OrderStatus.CREATED)
    stop_loss: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    broker_order_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class AuditLog(Base):
    """Append-only event log. No UPDATE or DELETE allowed."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    event_data: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_audit_log_event_type", "event_type"),
        Index("ix_audit_log_timestamp", "timestamp"),
    )


class KillSwitchEvent(Base):
    __tablename__ = "kill_switch_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    triggered_by: Mapped[str] = mapped_column(String(100), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
