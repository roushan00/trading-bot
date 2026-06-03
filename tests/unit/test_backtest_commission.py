from decimal import Decimal

from backtesting.commission import calculate_buy_cost, calculate_sell_proceeds, round_trip_cost


def test_buy_cost__includes_brokerage_and_slippage() -> None:
    result = calculate_buy_cost(Decimal("1000"), 100)
    assert result["fill_price"] > Decimal("1000")  # slippage added
    assert result["brokerage"] > Decimal("0")
    assert result["total_cost"] > Decimal("100000")


def test_sell_proceeds__includes_stt() -> None:
    result = calculate_sell_proceeds(Decimal("1000"), 100)
    assert result["fill_price"] < Decimal("1000")  # slippage deducted
    assert result["stt"] > Decimal("0")
    assert result["net_proceeds"] < Decimal("100000")


def test_round_trip__fees_visible() -> None:
    result = round_trip_cost(Decimal("1000"), Decimal("1000"), 100)
    assert result["total_fees"] > Decimal("0")
    assert result["pnl"] < Decimal("0")  # breakeven trade has negative P&L due to fees


def test_round_trip__profitable_trade() -> None:
    result = round_trip_cost(Decimal("1000"), Decimal("1050"), 100)
    assert result["pnl"] > Decimal("0")
    # But less than naive (1050-1000)*100 = 5000 due to fees
    assert result["pnl"] < Decimal("5000")


def test_commission_rates__match_spec() -> None:
    buy = calculate_buy_cost(Decimal("10000"), 1, slippage_rate=Decimal("0"))
    # 0.03% of 10000 = 3
    assert abs(buy["brokerage"] - Decimal("3")) < Decimal("0.01")

    sell = calculate_sell_proceeds(Decimal("10000"), 1, slippage_rate=Decimal("0"))
    # STT: 0.025% of 10000 = 2.5
    assert abs(sell["stt"] - Decimal("2.5")) < Decimal("0.01")
