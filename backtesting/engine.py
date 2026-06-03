import argparse
from datetime import datetime
from decimal import Decimal

import backtrader as bt
import structlog

from backtesting.commission import BROKERAGE_RATE, SLIPPAGE_RATE, STT_RATE
from backtesting.metrics import compute_metrics
from config.constants import IST

logger = structlog.get_logger(__name__)


class TradingCommission(bt.CommInfoBase):
    params = (
        ("commission", float(BROKERAGE_RATE)),
        ("stocklike", True),
        ("commtype", bt.CommInfoBase.COMM_PERC),
    )

    def _getcommission(self, size: float, price: float, pseudoexec: bool) -> float:
        base_comm = abs(size) * price * self.p.commission
        if size < 0:  # sell side STT
            base_comm += abs(size) * price * float(STT_RATE)
        return base_comm


class BacktestEngine:
    def __init__(
        self,
        initial_capital: float = 100000.0,
        slippage_pct: float = float(SLIPPAGE_RATE) * 100,
    ) -> None:
        self._initial_capital = initial_capital
        self._slippage_pct = slippage_pct

    def run(
        self,
        strategy_class: type[bt.Strategy],
        data_feed: bt.feeds.DataBase,
        strategy_kwargs: dict | None = None,
    ) -> dict:
        cerebro = bt.Cerebro()

        cerebro.addstrategy(strategy_class, **(strategy_kwargs or {}))
        cerebro.adddata(data_feed)

        cerebro.broker.setcash(self._initial_capital)
        cerebro.broker.addcommissioninfo(TradingCommission())
        cerebro.broker.set_slippage_perc(self._slippage_pct / 100)

        cerebro.addobserver(bt.observers.Value)
        cerebro.addobserver(bt.observers.Trades)
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe", riskfreerate=0.06)
        cerebro.addanalyzer(bt.analyzers.Returns, _name="returns")
        cerebro.addanalyzer(bt.analyzers.TimeReturn, _name="daily_returns")

        logger.info(
            "backtest_starting",
            strategy=strategy_class.__name__,
            capital=self._initial_capital,
        )

        results = cerebro.run()
        strat = results[0]

        final_value = cerebro.broker.getvalue()
        trade_analyzer = strat.analyzers.trades.get_analysis()
        drawdown_analyzer = strat.analyzers.drawdown.get_analysis()
        daily_returns_analyzer = strat.analyzers.daily_returns.get_analysis()

        daily_returns = list(daily_returns_analyzer.values())

        equity_curve = [self._initial_capital]
        for r in daily_returns:
            equity_curve.append(equity_curve[-1] * (1 + r))

        total_trades = trade_analyzer.get("total", {}).get("total", 0)
        won = trade_analyzer.get("won", {}).get("total", 0)
        lost = trade_analyzer.get("lost", {}).get("total", 0)

        won_pnl = trade_analyzer.get("won", {}).get("pnl", {}).get("total", 0)
        lost_pnl = abs(trade_analyzer.get("lost", {}).get("pnl", {}).get("total", 0))

        result = {
            "initial_capital": self._initial_capital,
            "final_value": final_value,
            "total_return_pct": (final_value - self._initial_capital) / self._initial_capital * 100,
            "max_drawdown_pct": drawdown_analyzer.get("max", {}).get("drawdown", 0),
            "total_trades": total_trades,
            "won": won,
            "lost": lost,
            "win_rate_pct": (won / total_trades * 100) if total_trades > 0 else 0,
            "profit_factor": (won_pnl / lost_pnl) if lost_pnl > 0 else float("inf") if won_pnl > 0 else 0,
            "equity_curve": equity_curve,
            "daily_returns": daily_returns,
        }

        logger.info(
            "backtest_complete",
            final_value=f"{final_value:.2f}",
            return_pct=f"{result['total_return_pct']:.2f}",
            trades=total_trades,
            win_rate=f"{result['win_rate_pct']:.1f}",
            max_dd=f"{result['max_drawdown_pct']:.2f}",
        )

        return result
