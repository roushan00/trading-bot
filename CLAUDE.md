# AI Trading Bot — Project Context for Claude Code

> **READ THIS FIRST.** This file is your single source of truth.
> Full design details are in `/docs/*.docx` — only open them when explicitly needed.

---

## Project Summary

An automated trading bot for the **Indian financial markets** (NSE/BSE equities and F&O).
The bot ingests live market data, runs rule-based strategies, applies risk controls, and executes trades through the **Angel One SmartAPI** broker.

This is **v1.0 — Path A "Learning Path"**. Scope is deliberately limited:
- Rule-based strategies only (no ML, no RL in v1.0)
- Paper trading only (no real money in v1.0)
- Minimal CLI + HTML dashboard (no React frontend in v1.0)

ML and RL are deferred to v2.0 after 8 weeks of successful paper trading.

---

## Tech Stack (Versions Pinned)

```
Python              3.11+
FastAPI             0.111.0
SQLAlchemy          2.0.30  (async with asyncpg)
PostgreSQL          15
Redis               7
Broker SDK          smartapi-python 1.3.9
Data libraries      pandas 2.2.2, pandas-ta 0.3.14b, numpy 1.26.4
Backtesting         backtrader 1.9.78.123
Task queue          celery 5.4.0, apscheduler 3.10.4
Testing             pytest 8.2.0, pytest-asyncio 0.23.6
Linting             ruff, black, mypy
Container           docker + docker-compose
```

---

## Folder Structure

```
trading-bot/
├── CLAUDE.md                   # ← you are here
├── docs/                       # PRD, HLD/LLD, Dev Plan (.docx files)
├── main.py                     # Application entrypoint
├── requirements.txt
├── docker-compose.yml
├── .env                        # NEVER commit; .env.example is the template
├── .env.example
├── .gitignore
├── alembic.ini
│
├── config/
│   ├── __init__.py
│   ├── settings.py             # Pydantic BaseSettings — loads .env
│   ├── logging.py              # structlog JSON config
│   └── constants.py            # Market hours, NSE holidays
│
├── data_ingestion/
│   ├── feed_handler.py         # SmartAPI WebSocket; reconnect with backoff
│   ├── normalizer.py           # Raw tick → Tick dataclass
│   ├── candle_builder.py       # Tick aggregation → OHLCV
│   └── data_store.py           # Redis + PostgreSQL writers
│
├── strategy_engine/
│   ├── base_strategy.py        # Abstract BaseStrategy class
│   ├── signal.py               # Signal dataclass
│   ├── runner.py               # Strategy lifecycle manager
│   └── strategies/
│       ├── ema_crossover.py
│       ├── rsi_reversal.py
│       └── orb.py              # Opening Range Breakout
│
├── risk_manager/
│   ├── risk_engine.py          # Sequential validation orchestrator
│   ├── kill_switch.py          # TRADING_HALTED flag + square-off
│   ├── position_sizer.py
│   ├── pnl_guard.py
│   └── stop_loss.py
│
├── order_execution/
│   ├── order_manager.py        # FSM: CREATED→VALIDATED→OPEN→COMPLETE
│   ├── brokers/
│   │   ├── base_broker.py      # Abstract interface
│   │   ├── paper_broker.py     # Simulated fills — DEFAULT in v1.0
│   │   └── smartapi.py         # Real broker — DISABLED in v1.0
│   └── retry.py
│
├── backtesting/
│   ├── engine.py               # Backtrader wrapper
│   ├── data_feed.py            # PostgreSQL → Backtrader feed
│   └── metrics.py              # Sharpe, CAGR, drawdown, win rate
│
├── audit_logger/
│   └── logger.py               # Append-only event log
│
├── pii_masking/
│   └── masker.py               # Mask PAN, Aadhaar, account numbers
│
├── dashboard/
│   ├── api/                    # FastAPI minimal — v1.0
│   │   ├── main.py
│   │   └── routes/
│   └── static/                 # Simple HTML — v1.0 only
│
└── tests/
    ├── unit/
    ├── integration/
    ├── fixtures/
    └── conftest.py
```

---

## Hard Rules (Never Violate These)

1. **PAPER_TRADING_MODE=true is the default and only mode for v1.0.**
   The SmartAPI live broker must NEVER be called. If you write code that calls `smartapi.place_order()` directly without checking `settings.paper_trading_mode`, that is a bug.

2. **Never put secrets in code.** API keys, passwords, TOTP secrets all live in `.env`. The `.env` file is gitignored.

3. **Never use random train/test split for time-series data.** Always walk-forward (time-ordered) split. (Applies to v2.0 ML — not relevant in v1.0.)

4. **Never modify the audit_log table.** It is append-only. No UPDATE, no DELETE.

5. **Every order must pass through RiskEngine.validate()** before reaching the broker. No exceptions, no shortcuts.

6. **Kill switch flag (`TRADING_HALTED` in Redis) is checked at the top of every order path.** If set, return immediately.

7. **All monetary values in code use `Decimal`, not `float`.** Python's float is unsafe for currency math.

8. **All timestamps are IST (`Asia/Kolkata`), stored as `TIMESTAMPTZ`.** Never use naive datetimes.

9. **No raw SQL strings.** Use SQLAlchemy ORM or `sqlalchemy.text()` with bound parameters.

10. **No `print()` statements in production code.** Use the structlog logger.

---

## Coding Conventions

- **Async first.** Use `async`/`await` for I/O (DB, Redis, HTTP, WebSocket). Sync only for pure CPU/math.
- **Type hints everywhere.** `def foo(x: int) -> str:` — not `def foo(x):`. mypy strict mode.
- **Dataclasses for value objects** (Signal, Order, Tick, Position). Pydantic for config and API schemas.
- **Errors are raised, not returned.** No tuples like `(result, error)`. Use exceptions + try/except at boundaries.
- **Logging style:** `logger.info("event_name", key1=val1, key2=val2)` — structured logs, not f-strings.
- **One class per file** for non-trivial classes (strategies, brokers, services).
- **Test naming:** `test_<module>__<scenario>__<expected>` e.g. `test_ema__golden_cross__emits_buy_signal`.
- **Imports:** stdlib → 3rd party → local; one block each; alphabetised within block.
- **No comments explaining what code does.** Code explains itself. Comments only explain *why* something non-obvious is done.

---

## Common Domain Vocabulary

| Term | Meaning |
|---|---|
| **OHLCV** | Open, High, Low, Close, Volume — candlestick data |
| **Tick** | Single price update from exchange |
| **Candle** | OHLCV aggregated over a timeframe (1min, 5min, 15min, 1hr, 1D) |
| **Signal** | Strategy output: BUY / SELL / HOLD on a symbol |
| **Order** | Signal validated by risk engine and sent to broker |
| **Fill** | Order completed by broker (fully or partially) |
| **Position** | Net holding in a symbol (positive = long, negative = short) |
| **P&L** | Profit and Loss — realised (closed) or unrealised (open) |
| **Drawdown** | Decline from peak portfolio value to a trough |
| **Slippage** | Difference between expected and actual fill price |
| **VWAP** | Volume Weighted Average Price |
| **NSE / BSE** | Indian stock exchanges |
| **F&O** | Futures and Options (derivatives) |
| **STT** | Securities Transaction Tax (0.025% on every sell) |
| **SEBI** | Securities and Exchange Board of India (regulator) |

---

## How We Work

This project is built **phase by phase**. The dev plan in `/docs/04_Dev_Plan_PathA.docx` has 5 phases with explicit task lists and evaluation criteria.

**Process for each task:**
1. Read the task description.
2. Implement minimal code to satisfy the task.
3. Write a unit test that proves it works.
4. Run the test. If it fails, fix the code (not the test).
5. Run the evaluation criteria for that task.
6. If pass → commit with message `phase X.Y: <task name>` and move on.
7. If fail → report what's failing and ask before proceeding.

**Never skip ahead to a future phase.** Don't write ML code while still in Phase 2.

**Don't add features not in the dev plan** unless they are obvious bug fixes or test infrastructure. If something seems missing, ask before adding.

---

## Current Status

**Phase:** All 5 phases complete. 101 unit tests passing.
**Next action:** Configure SmartAPI credentials in `.env`, start paper trading with `python main.py`.

---

## Useful Commands

```bash
# Start infrastructure
docker-compose up -d

# Run database migrations
alembic upgrade head

# Run all tests
pytest tests/ -v

# Run a single backtest
python -m backtesting.runner --strategy ema_crossover --symbol RELIANCE --from 2024-01-01

# Start trading engine (paper mode)
python main.py

# Start dashboard
uvicorn dashboard.api.main:app --reload --port 8000

# Trigger kill switch
python -m risk_manager.kill_switch

# Check Redis
docker exec -it trading-bot_redis_1 redis-cli
```

---

## Documents — Open Only When Needed

- `docs/01_PRD.docx` — Product requirements; read for "what" we're building
- `docs/02_HLD_LLD.docx` — Architecture and design; read for "how" components fit together
- `docs/04_Dev_Plan_PathA.docx` — Phase-by-phase plan with tasks and evaluation criteria; read at the start of each phase

---

## When in Doubt

- If a design decision is ambiguous, **ask the user** rather than guessing.
- If a task seems to require new dependencies, **ask before installing**.
- If a test is hard to write, the code is probably wrong — **refactor the code**, don't skip the test.
- If you've been working on the same task for more than 30 minutes, **stop and explain what's blocking you**.
