from datetime import datetime

import backtrader as bt
import pandas as pd
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

import asyncio


class PostgresDataFeed(bt.feeds.PandasData):
    params = (
        ("datetime", "timestamp"),
        ("open", "open"),
        ("high", "high"),
        ("low", "low"),
        ("close", "close"),
        ("volume", "volume"),
        ("openinterest", None),
    )


async def fetch_ohlcv_data(
    session_factory: async_sessionmaker[AsyncSession],
    symbol: str,
    timeframe: str,
    from_date: datetime,
    to_date: datetime,
) -> pd.DataFrame:
    async with session_factory() as session:
        result = await session.execute(
            text("""
                SELECT timestamp, open, high, low, close, volume
                FROM ohlcv
                WHERE symbol = :symbol
                  AND timeframe = :timeframe
                  AND timestamp >= :from_date
                  AND timestamp <= :to_date
                ORDER BY timestamp ASC
            """),
            {
                "symbol": symbol,
                "timeframe": timeframe,
                "from_date": from_date,
                "to_date": to_date,
            },
        )
        rows = result.fetchall()

    if not rows:
        return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

    df = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["open"] = df["open"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    df["close"] = df["close"].astype(float)
    df["volume"] = df["volume"].astype(int)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def load_feed_sync(
    session_factory: async_sessionmaker[AsyncSession],
    symbol: str,
    timeframe: str,
    from_date: datetime,
    to_date: datetime,
) -> PostgresDataFeed | None:
    loop = asyncio.new_event_loop()
    try:
        df = loop.run_until_complete(
            fetch_ohlcv_data(session_factory, symbol, timeframe, from_date, to_date)
        )
    finally:
        loop.close()

    if df.empty:
        return None

    df = df.set_index("timestamp")
    return PostgresDataFeed(dataname=df)
