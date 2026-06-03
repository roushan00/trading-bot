import math

from backtesting.metrics import compute_cagr, compute_max_drawdown, compute_sharpe


def test_sharpe__positive_returns__positive_sharpe() -> None:
    # Varying positive returns so std > 0
    returns = [0.008 + 0.004 * (i % 3) for i in range(252)]
    sharpe = compute_sharpe(returns, risk_free_rate=0.06)
    assert sharpe > 0


def test_sharpe__negative_returns__negative_sharpe() -> None:
    returns = [-0.005 + 0.002 * (i % 3) for i in range(252)]
    sharpe = compute_sharpe(returns, risk_free_rate=0.06)
    assert sharpe < 0


def test_sharpe__empty_returns__zero() -> None:
    assert compute_sharpe([]) == 0.0


def test_sharpe__manual_computation__matches() -> None:
    returns = [0.005, 0.01, -0.003, 0.007, 0.002]
    sharpe1 = compute_sharpe(returns, risk_free_rate=0.06)
    # Recompute manually
    import numpy as np
    arr = np.array(returns)
    daily_rf = (1.06) ** (1 / 252) - 1
    excess = arr - daily_rf
    manual = float(np.mean(excess)) / float(np.std(excess, ddof=1)) * math.sqrt(252)
    assert abs(sharpe1 - manual) < 0.01


def test_cagr__doubles_in_one_year() -> None:
    cagr = compute_cagr(100000, 200000, 1.0)
    assert abs(cagr - 100.0) < 0.1


def test_cagr__zero_initial__returns_zero() -> None:
    assert compute_cagr(0, 100, 1.0) == 0.0


def test_max_drawdown__no_drawdown__zero() -> None:
    curve = [100, 101, 102, 103, 104]
    assert compute_max_drawdown(curve) == 0.0


def test_max_drawdown__50pct_drop() -> None:
    curve = [100, 80, 50, 60, 70]
    dd = compute_max_drawdown(curve)
    assert abs(dd - 50.0) < 0.1


def test_max_drawdown__recovery_then_new_drop() -> None:
    curve = [100, 90, 95, 110, 88]
    dd = compute_max_drawdown(curve)
    assert abs(dd - 20.0) < 0.1  # 110 -> 88 = 20%
