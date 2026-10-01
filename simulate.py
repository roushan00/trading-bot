"""
Full pipeline simulation — no PostgreSQL, Redis, or SmartAPI credentials required.

Wires: SimulatedFeedHandler → CandleBuilder → Strategies → RiskEngine → PaperBroker

Usage:
    python simulate.py                            # 5 days, 300x speed (~6 min total)
    python simulate.py --days 10 --speed 600      # 10 days, faster
    python simulate.py --symbols RELIANCE TCS     # specific symbols
    python simulate.py --seed 42                  # reproducible run
"""

import argparse
import asyncio
import sys
from decimal import Decimal
from typing import Any

import pandas as pd
import structlog

import config.logging  # noqa: F401 — triggers structlog setup
from config.settings import settings
from data_ingestion.candle_builder import Candle, CandleBuilder
from data_ingestion.sim_feed import DEFAULT_SYMBOLS, SimulatedFeedHandler
from order_execution.brokers.paper_broker import PaperBroker
from risk_manager.kill_switch import KillSwitchCheck
from risk_manager.pnl_guard import DailyPnLGuard
from risk_manager.position_sizer import DuplicatePositionGuard, MaxPositionCapCheck
from risk_manager.risk_engine import RiskEngine
from strategy_engine.signal import Direction, Signal
from strategy_engine.strategies.ema_crossover import EMACrossover
from strategy_engine.strategies.orb import OpeningRangeBreakout
from strategy_engine.strategies.rsi_reversal import RSIReversal

logger = structlog.get_logger(__name__)


class _MockRedis:
    """In-memory Redis stub — no Redis server needed."""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self._store.get(key)

    async def set(self, key: str, value: str) -> None:
        self._store[key] = value

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)


class SimulationEngine:
    def __init__(self, initial_capital: Decimal) -> None:
        self._initial_capital = initial_capital
        self._capital = initial_capital
        self._broker = PaperBroker(slippage_pct=Decimal("0.05"))
        self._mock_redis = _MockRedis()

        self._risk_engine = RiskEngine(checks=[
            KillSwitchCheck(self._mock_redis),
            DailyPnLGuard(),
            MaxPositionCapCheck(),
            DuplicatePositionGuard(),
        ])

        self._strategies = [
            OpeningRangeBreakout(volume_multiplier=1.5),
            EMACrossover(fast_period=9, slow_period=21),
            RSIReversal(),
        ]

        # strategy_name -> "symbol:timeframe" -> pd.DataFrame
        self._candle_buffers: dict[str, dict[str, pd.DataFrame]] = {}

        self._order_id = 0
        self._trades: list[dict[str, Any]] = []
        self._rejected: list[dict[str, Any]] = []

    async def on_candle(self, candle: Candle) -> None:
        for strategy in self._strategies:
            if strategy.timeframe != candle.timeframe:
                continue

            buf_key = f"{candle.symbol}:{candle.timeframe}"
            strat_bufs = self._candle_buffers.setdefault(strategy.name, {})

            if buf_key not in strat_bufs:
                strat_bufs[buf_key] = pd.DataFrame(
                    columns=["timestamp", "open", "high", "low", "close", "volume", "symbol"]
                )

            df = strat_bufs[buf_key]
            new_row = pd.DataFrame([{
                "timestamp": candle.timestamp,
                "open": float(candle.open),
                "high": float(candle.high),
                "low": float(candle.low),
                "close": float(candle.close),
                "volume": candle.volume,
                "symbol": candle.symbol,
            }])
            df = pd.concat([df, new_row], ignore_index=True)
            if len(df) > 200:
                df = df.iloc[-200:].reset_index(drop=True)
            # Ensure numeric columns are float64 — pandas_ta's numba backend
            # rejects object-dtype arrays produced by pd.concat on empty frames.
            for col in ("open", "high", "low", "close"):
                df[col] = df[col].astype(float)
            strat_bufs[buf_key] = df

            signal = strategy.on_candle(df.copy())
            if signal is not None:
                await self._handle_signal(signal)

    async def _handle_signal(self, signal: Signal) -> None:
        positions = await self._broker.get_positions()
        pos_map = {p["symbol"]: p for p in positions}
        current_pos = pos_map.get(signal.symbol, {})
        current_qty = int(current_pos.get("quantity", 0))
        existing_value = Decimal(str(abs(current_qty))) * signal.price

        # Size position at 1% capital risk per trade
        quantity = max(int(self._capital * Decimal("0.01") / signal.price), 1)
        daily_pnl_pct = Decimal("0")  # simplified; no intraday P&L tracking yet

        context: dict[str, Any] = {
            "portfolio_value": self._capital,
            "existing_position_value": existing_value,
            "proposed_quantity": quantity,
            "current_position_qty": current_qty,
            "daily_pnl_pct": daily_pnl_pct,
            "current_drawdown_pct": Decimal("0"),
            "quantity": quantity,
        }

        passed, results = await self._risk_engine.validate(signal, context)
        if not passed:
            failed = next(r for r in results if not r.passed)
            self._rejected.append({
                "symbol": signal.symbol,
                "direction": signal.direction.value,
                "strategy": signal.strategy_name,
                "reason": failed.reason,
            })
            logger.info(
                "signal_rejected",
                symbol=signal.symbol,
                strategy=signal.strategy_name,
                reason=failed.reason,
            )
            return

        self._order_id += 1
        fill = await self._broker.place_order(
            symbol=signal.symbol,
            direction=signal.direction.value,
            quantity=quantity,
            price=signal.price,
            order_id=self._order_id,
        )

        self._trades.append({
            "order_id": self._order_id,
            "symbol": signal.symbol,
            "direction": signal.direction.value,
            "quantity": quantity,
            "fill_price": fill["fill_price"],
            "strategy": signal.strategy_name,
            "timestamp": signal.timestamp,
        })

        # Track capital: BUY depletes cash, SELL returns cash
        if signal.direction == Direction.BUY:
            self._capital -= fill["fill_price"] * Decimal(str(quantity))
        else:
            self._capital += fill["fill_price"] * Decimal(str(quantity))

    async def print_summary(self) -> None:
        sep = "=" * 70
        print(f"\n{sep}")
        print("  PAPER TRADING SIMULATION SUMMARY")
        print(sep)
        print(f"  Initial capital  : Rs.{float(self._initial_capital):>12,.2f}")
        print(f"  Remaining cash   : Rs.{float(self._capital):>12,.2f}")
        print(f"  Total trades     : {len(self._trades)}")
        print(f"  Rejected signals : {len(self._rejected)}")

        positions = await self._broker.get_positions()
        if positions:
            print(f"\n  OPEN POSITIONS:")
            for p in positions:
                print(f"    {p['symbol']:<12} qty={p['quantity']:>5}  avg_price=Rs.{float(p['avg_price']):,.2f}")

        if self._trades:
            print(f"\n  TRADE LOG:")
            header = f"  {'#':>3}  {'Symbol':<10} {'Dir':<5} {'Qty':>5}  {'Fill(Rs.)':>10}  {'Strategy':<18}  Timestamp"
            print(header)
            print(f"  {'-'*3}  {'-'*10} {'-'*5} {'-'*5}  {'-'*10}  {'-'*18}  {'-'*19}")
            for t in self._trades:
                ts = str(t["timestamp"])[:19]
                print(
                    f"  {t['order_id']:>3}  {t['symbol']:<10} {t['direction']:<5} "
                    f"{t['quantity']:>5}  Rs.{float(t['fill_price']):>10.2f}  "
                    f"{t['strategy']:<18}  {ts}"
                )
        else:
            print("\n  No trades executed.")
            print("  Strategies need enough candle history to produce signals:")
            print("    ORB          : signals within first 30 min of market open")
            print("    EMA Crossover: needs 23+ 15-min candles (~1 day)")
            print("    RSI Reversal : needs 22+ hourly candles (~4 days)")
            print("  Try: python simulate.py --days 10 --seed 42")

        print(sep)


async def run_simulation(
    num_days: int,
    speed: int,
    symbol_names: list[str],
    seed: int | None,
) -> None:
    symbols = {s: DEFAULT_SYMBOLS[s] for s in symbol_names if s in DEFAULT_SYMBOLS}
    unknown = [s for s in symbol_names if s not in DEFAULT_SYMBOLS]
    if unknown:
        logger.warning("unknown_symbols_skipped", symbols=unknown, available=list(DEFAULT_SYMBOLS.keys()))
    if not symbols:
        logger.error("no_valid_symbols", available=list(DEFAULT_SYMBOLS.keys()))
        sys.exit(1)

    estimated_real_sec = int(22500 * num_days / speed)
    logger.info(
        "simulation_starting",
        days=num_days,
        speed=f"{speed}x",
        symbols=list(symbols.keys()),
        estimated_duration_sec=estimated_real_sec,
    )
    print(f"\nSimulating {num_days} trading day(s) at {speed}x speed.")
    print(f"Estimated real-world time: ~{estimated_real_sec}s ({estimated_real_sec // 60}m {estimated_real_sec % 60}s)\n")

    engine = SimulationEngine(initial_capital=settings.INITIAL_CAPITAL)
    candle_builder = CandleBuilder(timeframes=["5min", "15min", "1hr"])
    feed = SimulatedFeedHandler(
        symbols=symbols,
        num_days=num_days,
        speed_multiplier=speed,
        random_seed=seed,
    )

    tick_count = 0
    async for tick in feed.generate_ticks():
        completed = candle_builder.on_tick(tick)
        for candle in completed:
            await engine.on_candle(candle)
        tick_count += 1
        if tick_count % 20000 == 0:
            positions = await engine._broker.get_positions()
            logger.info(
                "sim_progress",
                ticks=tick_count,
                trades=len(engine._trades),
                open_positions=len(positions),
            )

    # Flush any partially-built candles at simulation end
    for candle in candle_builder.flush_all():
        await engine.on_candle(candle)

    await engine.print_summary()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the full trading pipeline with simulated market data."
    )
    parser.add_argument("--days", type=int, default=5,
                        help="Trading days to simulate (default: 5)")
    parser.add_argument("--speed", type=int, default=300,
                        help="Speed multiplier — 300 = ~75s per day (default: 300)")
    parser.add_argument("--symbols", nargs="+", default=list(DEFAULT_SYMBOLS.keys()),
                        help=f"Symbols to simulate (default: {list(DEFAULT_SYMBOLS.keys())})")
    parser.add_argument("--seed", type=int, default=None,
                        help="Random seed for reproducible results")
    args = parser.parse_args()

    asyncio.run(run_simulation(args.days, args.speed, args.symbols, args.seed))


if __name__ == "__main__":
    main()
