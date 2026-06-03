import redis.asyncio as redis
import structlog

from config.settings import settings
from strategy_engine.signal import Signal

logger = structlog.get_logger(__name__)

SIGNAL_QUEUE_KEY = "signals:queue"


class SignalQueue:
    def __init__(self) -> None:
        self._redis: redis.Redis | None = None

    async def _get_redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
        return self._redis

    async def push(self, signal: Signal) -> None:
        r = await self._get_redis()
        await r.lpush(SIGNAL_QUEUE_KEY, signal.to_json())
        logger.info(
            "signal_queued",
            strategy=signal.strategy_name,
            symbol=signal.symbol,
            direction=signal.direction.value,
        )

    async def pop(self, timeout: int = 0) -> Signal | None:
        r = await self._get_redis()
        result = await r.brpop(SIGNAL_QUEUE_KEY, timeout=timeout)
        if result:
            _, raw = result
            return Signal.from_json(raw)
        return None

    async def length(self) -> int:
        r = await self._get_redis()
        return await r.llen(SIGNAL_QUEUE_KEY)

    async def close(self) -> None:
        if self._redis:
            await self._redis.close()
