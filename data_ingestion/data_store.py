import json
from datetime import datetime
from decimal import Decimal

import redis.asyncio as redis
import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config.constants import IST
from config.settings import settings
from data_ingestion.candle_builder import Candle
from data_ingestion.normalizer import Tick

logger = structlog.get_logger(__name__)

TICK_KEY_PREFIX = "tick:latest:"
TICK_CHANNEL_PREFIX = "tick:channel:"
CANDLE_BATCH_SIZE = 50


class RedisTickCache:
    def __init__(self) -> None:
        self._redis: redis.Redis | None = None

    async def _get_redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
        return self._redis

    async def store_tick(self, tick: Tick) -> None:
        r = await self._get_redis()
        key = f"{TICK_KEY_PREFIX}{tick.symbol}"
        tick_data = tick.to_dict()
        pipe = r.pipeline()
        pipe.set(key, json.dumps(tick_data), ex=300)
        pipe.publish(f"{TICK_CHANNEL_PREFIX}{tick.symbol}", json.dumps(tick_data))
        await pipe.execute()

    async def get_latest_tick(self, symbol: str) -> Tick | None:
        r = await self._get_redis()
        key = f"{TICK_KEY_PREFIX}{symbol}"
        data = await r.get(key)
        if data:
            return Tick.from_dict(json.loads(data))
        return None

    async def close(self) -> None:
        if self._redis:
            await self._redis.close()


class PostgresCandleWriter:
    def __init__(self, session_factory: object) -> None:
        self._session_factory = session_factory
        self._buffer: list[Candle] = []

    async def write_candle(self, candle: Candle) -> None:
        self._buffer.append(candle)
        if len(self._buffer) >= CANDLE_BATCH_SIZE:
            await self.flush()

    async def flush(self) -> None:
        if not self._buffer:
            return

        batch = self._buffer[:]
        self._buffer.clear()

        async with self._session_factory() as session:
            await self._batch_upsert(session, batch)

    async def _batch_upsert(self, session: AsyncSession, candles: list[Candle]) -> None:
        stmt = text("""
            INSERT INTO ohlcv (symbol, timeframe, timestamp, open, high, low, close, volume)
            VALUES (:symbol, :timeframe, :timestamp, :open, :high, :low, :close, :volume)
            ON CONFLICT (symbol, timeframe, timestamp)
            DO UPDATE SET
                open = EXCLUDED.open,
                high = EXCLUDED.high,
                low = EXCLUDED.low,
                close = EXCLUDED.close,
                volume = EXCLUDED.volume
        """)

        params = [
            {
                "symbol": c.symbol,
                "timeframe": c.timeframe,
                "timestamp": c.timestamp,
                "open": c.open,
                "high": c.high,
                "low": c.low,
                "close": c.close,
                "volume": c.volume,
            }
            for c in candles
        ]

        await session.execute(stmt, params)
        await session.commit()
        logger.info("candles_written", count=len(candles))
