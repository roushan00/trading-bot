from decimal import Decimal

BROKERAGE_RATE = Decimal("0.0003")   # 0.03%
STT_RATE = Decimal("0.00025")        # 0.025% on sell
SLIPPAGE_RATE = Decimal("0.0005")    # 0.05%


def calculate_buy_cost(price: Decimal, quantity: int, slippage_rate: Decimal = SLIPPAGE_RATE) -> dict:
    slippage = price * slippage_rate
    fill_price = price + slippage
    gross_value = fill_price * quantity
    brokerage = gross_value * BROKERAGE_RATE
    total_cost = gross_value + brokerage
    return {
        "fill_price": fill_price,
        "gross_value": gross_value,
        "brokerage": brokerage,
        "stt": Decimal("0"),
        "slippage": slippage * quantity,
        "total_cost": total_cost,
    }


def calculate_sell_proceeds(price: Decimal, quantity: int, slippage_rate: Decimal = SLIPPAGE_RATE) -> dict:
    slippage = price * slippage_rate
    fill_price = price - slippage
    gross_value = fill_price * quantity
    brokerage = gross_value * BROKERAGE_RATE
    stt = gross_value * STT_RATE
    net_proceeds = gross_value - brokerage - stt
    return {
        "fill_price": fill_price,
        "gross_value": gross_value,
        "brokerage": brokerage,
        "stt": stt,
        "slippage": slippage * quantity,
        "net_proceeds": net_proceeds,
    }


def round_trip_cost(buy_price: Decimal, sell_price: Decimal, quantity: int) -> dict:
    buy = calculate_buy_cost(buy_price, quantity)
    sell = calculate_sell_proceeds(sell_price, quantity)
    pnl = sell["net_proceeds"] - buy["total_cost"]
    total_fees = buy["brokerage"] + sell["brokerage"] + sell["stt"] + buy["slippage"] + sell["slippage"]
    return {
        "buy": buy,
        "sell": sell,
        "pnl": pnl,
        "total_fees": total_fees,
    }
