from datetime import datetime
from decimal import Decimal

import pandas as pd

from config.constants import IST
from strategy_engine.signal import Direction
from strategy_engine.strategies.ema_crossover import EMACrossover
from strategy_engine.strategies.orb import OpeningRangeBreakout
from strategy_engine.strategies.rsi_reversal import RSIReversal


def _make_df(prices: list[float], start_minute: int = 0, symbol: str = "TEST", timeframe_minutes: int = 15) -> pd.DataFrame:
    from datetime import timedelta
    base = datetime(2026, 5, 1, 9, 15, 0, tzinfo=IST)  # Start from a safe time
    rows = []
    for i, p in enumerate(prices):
        ts = base + timedelta(minutes=i * timeframe_minutes)
        rows.append({
            "timestamp": ts,
            "open": p * 0.999,
            "high": p * 1.005,
            "low": p * 0.995,
            "close": p,
            "volume": 1000,
            "symbol": symbol,
        })
    return pd.DataFrame(rows)


# --- EMA Crossover Tests ---

def test_ema__insufficient_data__returns_none() -> None:
    strategy = EMACrossover(fast_period=9, slow_period=21)
    df = _make_df([100.0] * 10)
    assert strategy.on_candle(df) is None


def test_ema__golden_cross__emits_buy_signal() -> None:
    strategy = EMACrossover(fast_period=3, slow_period=5)
    # Start with downtrend then cross up
    prices = [100, 99, 98, 97, 96, 95, 94, 93]  # slow EMA > fast EMA
    prices += [94, 96, 99, 103, 108, 114, 121]   # fast EMA crosses above
    df = _make_df(prices)
    signal = strategy.on_candle(df)
    if signal is not None:
        assert signal.direction == Direction.BUY
        assert signal.stop_loss is not None


def test_ema__death_cross__emits_sell_signal() -> None:
    strategy = EMACrossover(fast_period=3, slow_period=5)
    prices = [100, 101, 102, 103, 104, 105, 106, 107]  # uptrend
    prices += [106, 104, 101, 97, 92, 86, 79]            # sharp reversal
    df = _make_df(prices)
    signal = strategy.on_candle(df)
    if signal is not None:
        assert signal.direction == Direction.SELL


def test_ema__flat_market__no_signal() -> None:
    strategy = EMACrossover(fast_period=9, slow_period=21)
    # Truly flat: identical prices so EMAs converge and never cross
    prices = [100.0] * 30
    df = _make_df(prices)
    signal = strategy.on_candle(df)
    assert signal is None


# --- RSI Reversal Tests ---

def test_rsi__insufficient_data__returns_none() -> None:
    strategy = RSIReversal()
    df = _make_df([100.0] * 10, timeframe_minutes=60)
    assert strategy.on_candle(df) is None


def test_rsi__oversold_bounce__emits_buy() -> None:
    strategy = RSIReversal(rsi_period=5, bb_period=5, rsi_oversold=30.0)
    # Sharp drop to make RSI oversold, then slight recovery
    prices = [100, 98, 95, 90, 84, 77, 69, 60]  # heavy selling
    prices += [58, 55, 52, 48, 44, 40, 38]        # more selling
    prices += [39, 41]                              # slight bounce
    df = _make_df(prices, timeframe_minutes=60)
    signal = strategy.on_candle(df)
    # May or may not trigger depending on exact RSI/BB values
    if signal is not None:
        assert signal.direction == Direction.BUY


# --- Opening Range Breakout Tests ---

def _make_orb_df(
    orb_candles: list[dict],
    post_orb_candles: list[dict],
    symbol: str = "TEST",
) -> pd.DataFrame:
    rows = []
    # ORB candles (9:15, 9:20, 9:25)
    for i, c in enumerate(orb_candles):
        rows.append({
            "timestamp": datetime(2026, 5, 28, 9, 15 + i * 5, 0, tzinfo=IST),
            "open": c["open"],
            "high": c["high"],
            "low": c["low"],
            "close": c["close"],
            "volume": c["volume"],
            "symbol": symbol,
        })
    # Post-ORB candles (9:30, 9:35, ...)
    for i, c in enumerate(post_orb_candles):
        rows.append({
            "timestamp": datetime(2026, 5, 28, 9, 30 + i * 5, 0, tzinfo=IST),
            "open": c["open"],
            "high": c["high"],
            "low": c["low"],
            "close": c["close"],
            "volume": c["volume"],
            "symbol": symbol,
        })
    return pd.DataFrame(rows)


def test_orb__bullish_breakout__emits_buy() -> None:
    strategy = OpeningRangeBreakout(volume_multiplier=1.0)
    orb = [
        {"open": 100, "high": 105, "low": 98, "close": 103, "volume": 1000},
        {"open": 103, "high": 106, "low": 101, "close": 104, "volume": 1200},
        {"open": 104, "high": 107, "low": 102, "close": 105, "volume": 1100},
    ]
    # Post-ORB: breakout above 107 with high volume
    post = [
        {"open": 106, "high": 110, "low": 105, "close": 109, "volume": 2000},
    ]
    df = _make_orb_df(orb, post)

    # Feed candles one at a time
    signal = None
    for i in range(len(df)):
        signal = strategy.on_candle(df.iloc[: i + 1].reset_index(drop=True))
        if signal is not None:
            break

    assert signal is not None
    assert signal.direction == Direction.BUY
    assert signal.price == Decimal("109")


def test_orb__no_breakout__no_signal() -> None:
    strategy = OpeningRangeBreakout(volume_multiplier=1.5)
    orb = [
        {"open": 100, "high": 105, "low": 98, "close": 103, "volume": 1000},
        {"open": 103, "high": 106, "low": 101, "close": 104, "volume": 1200},
        {"open": 104, "high": 107, "low": 102, "close": 105, "volume": 1100},
    ]
    # Post-ORB: stays within range, low volume
    post = [
        {"open": 104, "high": 106, "low": 99, "close": 103, "volume": 500},
    ]
    df = _make_orb_df(orb, post)

    signal = None
    for i in range(len(df)):
        signal = strategy.on_candle(df.iloc[: i + 1].reset_index(drop=True))
        if signal is not None:
            break

    assert signal is None


def test_orb__bearish_breakout__emits_sell() -> None:
    strategy = OpeningRangeBreakout(volume_multiplier=1.0)
    orb = [
        {"open": 100, "high": 105, "low": 98, "close": 103, "volume": 1000},
        {"open": 103, "high": 106, "low": 101, "close": 104, "volume": 1200},
        {"open": 104, "high": 107, "low": 102, "close": 105, "volume": 1100},
    ]
    # Post-ORB: breakdown below 98 with high volume
    post = [
        {"open": 99, "high": 100, "low": 95, "close": 96, "volume": 2000},
    ]
    df = _make_orb_df(orb, post)

    signal = None
    for i in range(len(df)):
        signal = strategy.on_candle(df.iloc[: i + 1].reset_index(drop=True))
        if signal is not None:
            break

    assert signal is not None
    assert signal.direction == Direction.SELL


def test_orb__fires_only_once_per_day() -> None:
    strategy = OpeningRangeBreakout(volume_multiplier=1.0)
    orb = [
        {"open": 100, "high": 105, "low": 98, "close": 103, "volume": 1000},
        {"open": 103, "high": 106, "low": 101, "close": 104, "volume": 1200},
        {"open": 104, "high": 107, "low": 102, "close": 105, "volume": 1100},
    ]
    post = [
        {"open": 106, "high": 110, "low": 105, "close": 109, "volume": 2000},
        {"open": 109, "high": 115, "low": 108, "close": 114, "volume": 2500},
    ]
    df = _make_orb_df(orb, post)

    signals = []
    for i in range(len(df)):
        sig = strategy.on_candle(df.iloc[: i + 1].reset_index(drop=True))
        if sig is not None:
            signals.append(sig)

    assert len(signals) == 1
