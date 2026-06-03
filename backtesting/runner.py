import argparse
import sys
from datetime import datetime

import structlog

from backtesting.bt_strategies import STRATEGY_MAP
from backtesting.data_feed import load_feed_sync
from backtesting.engine import BacktestEngine
from config.constants import IST
from config.database import async_session_factory
from config.settings import settings

logger = structlog.get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run backtest for a strategy")
    parser.add_argument("--strategy", required=True, choices=list(STRATEGY_MAP.keys()))
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--timeframe", default="1D")
    parser.add_argument("--from", dest="from_date", required=True, help="Start date YYYY-MM-DD")
    parser.add_argument("--to", dest="to_date", default=None, help="End date YYYY-MM-DD")
    parser.add_argument("--capital", type=float, default=float(settings.INITIAL_CAPITAL))
    args = parser.parse_args()

    from_dt = datetime.strptime(args.from_date, "%Y-%m-%d").replace(tzinfo=IST)
    to_dt = (
        datetime.strptime(args.to_date, "%Y-%m-%d").replace(tzinfo=IST)
        if args.to_date
        else datetime.now(tz=IST)
    )

    strategy_class = STRATEGY_MAP[args.strategy]

    logger.info(
        "loading_data",
        symbol=args.symbol,
        timeframe=args.timeframe,
        from_date=args.from_date,
        to_date=args.to_date or "now",
    )

    feed = load_feed_sync(async_session_factory, args.symbol, args.timeframe, from_dt, to_dt)
    if feed is None:
        logger.error("no_data_found", symbol=args.symbol, timeframe=args.timeframe)
        sys.exit(1)

    engine = BacktestEngine(initial_capital=args.capital)
    result = engine.run(strategy_class, feed)

    print(f"\n{'='*50}")
    print(f"Backtest: {args.strategy} on {args.symbol}")
    print(f"Period: {args.from_date} to {args.to_date or 'now'}")
    print(f"{'='*50}")
    print(f"Initial Capital: ₹{result['initial_capital']:,.2f}")
    print(f"Final Value:     ₹{result['final_value']:,.2f}")
    print(f"Total Return:    {result['total_return_pct']:.2f}%")
    print(f"Max Drawdown:    {result['max_drawdown_pct']:.2f}%")
    print(f"Total Trades:    {result['total_trades']}")
    print(f"Win Rate:        {result['win_rate_pct']:.1f}%")
    print(f"Profit Factor:   {result['profit_factor']:.2f}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
