import asyncio
import math
import random
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import AsyncIterator

import structlog

from config.constants import IST
from data_ingestion.normalizer import Tick

logger = structlog.get_logger(__name__)

MARKET_OPEN = (9, 15)
MARKET_CLOSE = (15, 30)

# Realistic NSE base prices
DEFAULT_SYMBOLS: dict[str, Decimal] = {
    "RELIANCE": Decimal("2800.00"),
    "INFY": Decimal("1500.00"),
    "TCS": Decimal("3800.00"),
}

# seconds in a trading year: 252 days * 6.25 hrs * 3600 s
_SECONDS_PER_TRADING_YEAR = 252 * 6.25 * 3600


class SimulatedFeedHandler:
    """Generates synthetic tick data using geometric Brownian motion.

    Replaces FeedHandler when no SmartAPI credentials are available.
    Each tick represents one simulated second of market activity.
    """

    def __init__(
        self,
        symbols: dict[str, Decimal] | None = None,
        num_days: int = 5,
        speed_multiplier: int = 300,
        annual_volatility: float = 0.20,
        random_seed: int | None = None,
    ) -> None:
        self._symbols = symbols or DEFAULT_SYMBOLS
        self._num_days = num_days
        self._speed = speed_multiplier
        # Per-second volatility derived from annual vol
        self._vol_per_sec = annual_volatility / math.sqrt(_SECONDS_PER_TRADING_YEAR)
        if random_seed is not None:
            random.seed(random_seed)

    def _weekdays_from(self, start: date, count: int) -> list[date]:
        days: list[date] = []
        current = start
        while len(days) < count:
            if current.weekday() < 5:  # Mon–Fri
                days.append(current)
            current += timedelta(days=1)
        return days

    async def generate_ticks(self) -> AsyncIterator[Tick]:
        today = datetime.now(tz=IST).date()
        trading_days = self._weekdays_from(today, self._num_days)
        prices = {sym: float(price) for sym, price in self._symbols.items()}
        real_sleep = 1.0 / self._speed

        for day in trading_days:
            open_h, open_m = MARKET_OPEN
            close_h, close_m = MARKET_CLOSE
            sim_time = datetime(day.year, day.month, day.day, open_h, open_m, 0, tzinfo=IST)
            market_close = sim_time.replace(hour=close_h, minute=close_m)
            day_ticks = 0

            logger.info("sim_day_starting", date=str(day))

            while sim_time < market_close:
                for symbol in self._symbols:
                    # GBM: S(t+dt) = S(t) * exp(sigma * dW)
                    dw = random.gauss(0, 1)
                    new_price = prices[symbol] * math.exp(self._vol_per_sec * dw)
                    prices[symbol] = new_price

                    ltp = Decimal(str(round(new_price, 2)))
                    volume = random.randint(200, 8000)

                    yield Tick(
                        symbol=symbol,
                        token=str(abs(hash(symbol)) % 100000),
                        ltp=ltp,
                        open=ltp,
                        high=ltp,
                        low=ltp,
                        close=ltp,
                        volume=volume,
                        timestamp=sim_time,
                    )

                sim_time += timedelta(seconds=1)
                day_ticks += 1
                await asyncio.sleep(real_sleep)

            logger.info("sim_day_complete", date=str(day), ticks=day_ticks)
