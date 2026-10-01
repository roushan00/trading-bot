# Phase 1 — Bug Fix Report

**Date:** 2026-10-01
**Scope:** Critical & Important issues in Phase 1 (config + data ingestion layer)
**Tests:** 101/101 passing after all fixes

---

## Critical Fixes

### 1. Naive Timestamps (normalizer.py, signal.py)
**Problem:** `datetime.fromisoformat()` on strings without timezone offset created naive datetimes, violating the project rule "never use naive datetimes."
**Fix:** Added `_ensure_ist()` static method to both `Tick` and `Signal` classes. If a parsed datetime has no `tzinfo`, it is tagged with IST (`Asia/Kolkata`).
**Files changed:**
- `data_ingestion/normalizer.py` — added `_ensure_ist()`, applied in `from_dict()`
- `strategy_engine/signal.py` — added `_ensure_ist()`, applied in `from_json()`

### 2. Async-Unaware on_tick Callback (feed_handler.py)
**Problem:** `on_tick` callback was typed as `Callable[[Tick], None]`. If an async coroutine was passed (needed for Redis/DB writes), it would silently return a coroutine object — never awaited, no error, no data stored.
**Fix:** Callback type now accepts both sync and async callables. If the result is awaitable, it is scheduled on the event loop via `asyncio.ensure_future` using `call_soon_threadsafe`.
**Files changed:**
- `data_ingestion/feed_handler.py` — updated type hint, added `inspect.isawaitable()` check in `on_data()`

### 3. Blocking WebSocket Connect (feed_handler.py)
**Problem:** `self._ws.connect()` is a blocking call (SmartWebSocketV2 runs its own event loop internally). Called inside an `async` method, it blocked the entire asyncio event loop — no other coroutines (Redis writes, strategy execution) could run.
**Fix:** Wrapped in `await loop.run_in_executor(None, self._ws.connect)` to offload to a thread.
**Files changed:**
- `data_ingestion/feed_handler.py` — line 113

---

## Important Fixes

### 4. Volume Accumulation Bug (candle_builder.py)
**Problem:** SmartAPI provides cumulative day volume (`volume_trade_for_the_day`), not per-tick delta. The old code summed raw values: `self.volume += tick.volume`, producing wildly inflated candle volumes. This would break volume-dependent strategies like ORB.
**Fix:** Added `_last_cumulative_volume` field to `CandleAccumulator`. First tick of each candle sets the baseline. Subsequent ticks compute `delta = tick.volume - _last_cumulative_volume` and add only the delta.
**Files changed:**
- `data_ingestion/candle_builder.py` — `CandleAccumulator.add_tick()`
- `tests/unit/test_data_candle_builder.py` — updated 2 tests to use cumulative volumes

### 5. setup_logging() Side Effect at Import (config/logging.py, main.py)
**Problem:** `setup_logging()` was called at the bottom of `config/logging.py` as a module-level side effect. Any import of `config.logging` (including in tests) immediately configured structlog globally, breaking test isolation.
**Fix:** Removed the auto-call from `config/logging.py`. Added explicit `setup_logging()` call in `main.py` before any logger is created.
**Files changed:**
- `config/logging.py` — removed `setup_logging()` call at line 28
- `main.py` — added `from config.logging import setup_logging` and `setup_logging()`

### 6. Redis Connection Race Condition (data_store.py)
**Problem:** `RedisTickCache._get_redis()` lazily initialized a shared connection without a lock. Under concurrent async access, two coroutines could both see `self._redis is None`, both call `from_url()`, creating two connections — one orphaned.
**Fix:** Added `asyncio.Lock()` with double-checked locking pattern.
**Files changed:**
- `data_ingestion/data_store.py` — `RedisTickCache.__init__()` and `_get_redis()`

### 7. Fee Rates Stored as Strings, Not Decimal (config/constants.py)
**Problem:** `BROKERAGE_RATE`, `STT_RATE`, `SLIPPAGE_RATE` were plain strings (`"0.0003"`), violating the project rule "all monetary values use Decimal."
**Fix:** Changed to `Decimal("0.0003")` etc. Added `from decimal import Decimal` import.
**Files changed:**
- `config/constants.py` — lines 44-47

---

## Known Remaining Items (deferred)

| Item | Severity | Location |
|---|---|---|
| f-string SQL in order_manager.py | Medium | `order_execution/order_manager.py:100` |
| Default DB credentials in settings.py | Low | `config/settings.py:21-22` |
| `session_factory` typed as `object` | Low | `data_ingestion/data_store.py:54` |
| `simulate.py` uses `print()` | Low | `simulate.py` |
| pandas-ta version mismatch | Low | `requirements.txt` vs CLAUDE.md |
| Hardcoded `"abc123"` subscription ID | Low | `data_ingestion/feed_handler.py:99` |
