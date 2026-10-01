import asyncio
import sys

import structlog

from config.logging import setup_logging
from config.settings import settings

setup_logging()

logger = structlog.get_logger(__name__)


async def main() -> None:
    logger.info(
        "trading_bot_starting",
        app_name=settings.APP_NAME,
        env=settings.APP_ENV,
        paper_mode=settings.PAPER_TRADING_MODE,
    )

    if not settings.PAPER_TRADING_MODE:
        logger.critical("live_trading_disabled", reason="v1.0 is paper trading only")
        sys.exit(1)

    logger.info("trading_bot_ready", mode="paper")


if __name__ == "__main__":
    asyncio.run(main())
