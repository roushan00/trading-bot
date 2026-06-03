import asyncio
from typing import Callable, TypeVar

import structlog

logger = structlog.get_logger(__name__)

T = TypeVar("T")


async def retry_async(
    func: Callable,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    *args,
    **kwargs,
) -> T:
    last_exception = None
    delay = base_delay

    for attempt in range(1, max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            if attempt == max_retries:
                break
            logger.warning(
                "retry_attempt",
                attempt=attempt,
                max_retries=max_retries,
                delay=delay,
                error=str(e)[:100],
            )
            await asyncio.sleep(delay)
            delay = min(delay * 2, max_delay)

    logger.error("retry_exhausted", max_retries=max_retries, error=str(last_exception)[:200])
    raise last_exception  # type: ignore[misc]
