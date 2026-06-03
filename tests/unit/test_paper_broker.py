from decimal import Decimal

import pytest

from order_execution.brokers.paper_broker import PaperBroker


@pytest.mark.asyncio
async def test_paper_broker__buy_order__fills_with_slippage() -> None:
    broker = PaperBroker(slippage_pct=Decimal("0.05"))
    result = await broker.place_order("RELIANCE", "BUY", 10, Decimal("2500"), order_id=1)
    assert result["status"] == "COMPLETE"
    assert result["fill_price"] > Decimal("2500")
    assert result["broker_order_id"].startswith("PAPER-")


@pytest.mark.asyncio
async def test_paper_broker__sell_order__fills_below_price() -> None:
    broker = PaperBroker(slippage_pct=Decimal("0.05"))
    await broker.place_order("RELIANCE", "BUY", 10, Decimal("2500"), order_id=1)
    result = await broker.place_order("RELIANCE", "SELL", 10, Decimal("2550"), order_id=2)
    assert result["status"] == "COMPLETE"
    assert result["fill_price"] < Decimal("2550")


@pytest.mark.asyncio
async def test_paper_broker__positions_tracked() -> None:
    broker = PaperBroker()
    await broker.place_order("RELIANCE", "BUY", 10, Decimal("2500"), order_id=1)
    positions = await broker.get_positions()
    assert len(positions) == 1
    assert positions[0]["symbol"] == "RELIANCE"
    assert positions[0]["quantity"] == 10


@pytest.mark.asyncio
async def test_paper_broker__position_cleared_on_full_sell() -> None:
    broker = PaperBroker()
    await broker.place_order("RELIANCE", "BUY", 10, Decimal("2500"), order_id=1)
    await broker.place_order("RELIANCE", "SELL", 10, Decimal("2550"), order_id=2)
    positions = await broker.get_positions()
    assert len(positions) == 0


@pytest.mark.asyncio
async def test_paper_broker__square_off_all__closes_positions() -> None:
    broker = PaperBroker()
    await broker.place_order("RELIANCE", "BUY", 10, Decimal("2500"), order_id=1)
    await broker.place_order("INFY", "BUY", 5, Decimal("1500"), order_id=2)
    results = await broker.square_off_all()
    assert len(results) == 2
    positions = await broker.get_positions()
    assert len(positions) == 0


@pytest.mark.asyncio
async def test_paper_broker__get_order_status() -> None:
    broker = PaperBroker()
    result = await broker.place_order("TCS", "BUY", 1, Decimal("3500"), order_id=1)
    status = await broker.get_order_status(result["broker_order_id"])
    assert status["status"] == "COMPLETE"


@pytest.mark.asyncio
async def test_paper_broker__unknown_order__returns_error() -> None:
    broker = PaperBroker()
    status = await broker.get_order_status("FAKE-123")
    assert "error" in status
