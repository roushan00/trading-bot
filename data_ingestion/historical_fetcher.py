from datetime import datetime, timedelta
from decimal import Decimal

import structlog
from SmartApi import SmartConnect

from config.constants import IST
from data_ingestion.auth import SmartAPIAuth
from data_ingestion.candle_builder import Candle
from data_ingestion.data_store import PostgresCandleWriter

logger = structlog.get_logger(__name__)

INTERVAL_MAP = {
    "1min": "ONE_MINUTE",
    "5min": "FIVE_MINUTE",
    "15min": "FIFTEEN_MINUTE",
    "1hr": "ONE_HOUR",
    "1D": "ONE_DAY",
}

MAX_DAYS_PER_REQUEST = {
    "1min": 30,
    "5min": 30,
    "15min": 90,
    "1hr": 365,
    "1D": 2000,
}


class HistoricalFetcher:
    def __init__(self, auth: SmartAPIAuth, candle_writer: PostgresCandleWriter) -> None:
        self._auth = auth
        self._candle_writer = candle_writer

    async def fetch_history(
        self,
        symbol: str,
        token: str,
        exchange: str,
        timeframe: str,
        from_date: datetime,
        to_date: datetime | None = None,
    ) -> int:
        if to_date is None:
            to_date = datetime.now(tz=IST)

        interval = INTERVAL_MAP.get(timeframe)
        if not interval:
            raise ValueError(f"Unsupported timeframe: {timeframe}")

        smart_connect = await self._auth.get_smart_connect()
        max_days = MAX_DAYS_PER_REQUEST[timeframe]
        total_candles = 0

        current_from = from_date
        while current_from < to_date:
            current_to = min(current_from + timedelta(days=max_days), to_date)

            try:
                params = {
                    "exchange": exchange,
                    "symboltoken": token,
                    "interval": interval,
                    "fromdate": current_from.strftime("%Y-%m-%d %H:%M"),
                    "todate": current_to.strftime("%Y-%m-%d %H:%M"),
                }
                response = smart_connect.getCandleData(params)

                if not response or response.get("status") is False:
                    error_msg = response.get("message", "Unknown") if response else "No response"
                    logger.warning(
                        "historical_fetch_failed",
                        symbol=symbol,
                        timeframe=timeframe,
                        error=error_msg,
                    )
                    current_from = current_to
                    continue

                data = response.get("data", [])
                if not data:
                    logger.debug("historical_no_data", symbol=symbol, from_date=str(current_from))
                    current_from = current_to
                    continue

                for row in data:
                    ts_str, o, h, l, c, v = row
                    ts = datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%S%z")
                    candle = Candle(
                        symbol=symbol,
                        timeframe=timeframe,
                        timestamp=ts,
                        open=Decimal(str(o)),
                        high=Decimal(str(h)),
                        low=Decimal(str(l)),
                        close=Decimal(str(c)),
                        volume=int(v),
                    )
                    await self._candle_writer.write_candle(candle)

                total_candles += len(data)
                logger.info(
                    "historical_batch_fetched",
                    symbol=symbol,
                    timeframe=timeframe,
                    count=len(data),
                    from_date=str(current_from.date()),
                    to_date=str(current_to.date()),
                )

            except Exception:
                logger.error(
                    "historical_fetch_error",
                    symbol=symbol,
                    exc_info=True,
                )

            current_from = current_to

        await self._candle_writer.flush()
        logger.info(
            "historical_fetch_complete",
            symbol=symbol,
            timeframe=timeframe,
            total_candles=total_candles,
        )
        return total_candles
