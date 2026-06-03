from dataclasses import dataclass
from decimal import Decimal
import math

import numpy as np


@dataclass
class BacktestMetrics:
    total_return_pct: float
    cagr_pct: float
    sharpe_ratio: float
    max_drawdown_pct: float
    win_rate_pct: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_win_pct: float
    avg_loss_pct: float
    profit_factor: float

    def summary(self) -> str:
        return (
            f"Total Return: {self.total_return_pct:.2f}%\n"
            f"CAGR: {self.cagr_pct:.2f}%\n"
            f"Sharpe Ratio: {self.sharpe_ratio:.2f}\n"
            f"Max Drawdown: {self.max_drawdown_pct:.2f}%\n"
            f"Win Rate: {self.win_rate_pct:.2f}%\n"
            f"Total Trades: {self.total_trades}\n"
            f"Winning: {self.winning_trades} | Losing: {self.losing_trades}\n"
            f"Avg Win: {self.avg_win_pct:.2f}% | Avg Loss: {self.avg_loss_pct:.2f}%\n"
            f"Profit Factor: {self.profit_factor:.2f}"
        )


def compute_sharpe(returns: list[float], risk_free_rate: float = 0.06, trading_days: int = 252) -> float:
    if len(returns) < 2:
        return 0.0
    arr = np.array(returns, dtype=float)
    daily_rf = (1 + risk_free_rate) ** (1.0 / trading_days) - 1
    excess = arr - daily_rf
    mean_excess = float(np.mean(excess))
    std = float(np.std(excess, ddof=1))
    if std < 1e-15:
        return 0.0 if abs(mean_excess) < 1e-15 else float("inf") if mean_excess > 0 else float("-inf")
    return mean_excess / std * math.sqrt(trading_days)


def compute_cagr(initial_value: float, final_value: float, years: float) -> float:
    if initial_value <= 0 or years <= 0:
        return 0.0
    return ((final_value / initial_value) ** (1 / years) - 1) * 100


def compute_max_drawdown(equity_curve: list[float]) -> float:
    if len(equity_curve) < 2:
        return 0.0
    peak = equity_curve[0]
    max_dd = 0.0
    for value in equity_curve:
        if value > peak:
            peak = value
        dd = (peak - value) / peak * 100 if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd
    return max_dd


def compute_metrics(
    trades: list[dict],
    equity_curve: list[float],
    initial_capital: float,
    trading_days: int,
) -> BacktestMetrics:
    final_value = equity_curve[-1] if equity_curve else initial_capital
    total_return = (final_value - initial_capital) / initial_capital * 100
    years = trading_days / 252 if trading_days > 0 else 1.0

    wins = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] <= 0]

    win_rate = len(wins) / len(trades) * 100 if trades else 0.0
    avg_win = np.mean([t["pnl_pct"] for t in wins]) if wins else 0.0
    avg_loss = np.mean([t["pnl_pct"] for t in losses]) if losses else 0.0

    gross_profit = sum(t["pnl"] for t in wins)
    gross_loss = abs(sum(t["pnl"] for t in losses))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf") if gross_profit > 0 else 0.0

    daily_returns = []
    for i in range(1, len(equity_curve)):
        if equity_curve[i - 1] > 0:
            daily_returns.append((equity_curve[i] - equity_curve[i - 1]) / equity_curve[i - 1])

    return BacktestMetrics(
        total_return_pct=total_return,
        cagr_pct=compute_cagr(initial_capital, final_value, years),
        sharpe_ratio=compute_sharpe(daily_returns),
        max_drawdown_pct=compute_max_drawdown(equity_curve),
        win_rate_pct=win_rate,
        total_trades=len(trades),
        winning_trades=len(wins),
        losing_trades=len(losses),
        avg_win_pct=float(avg_win),
        avg_loss_pct=float(avg_loss),
        profit_factor=profit_factor,
    )
