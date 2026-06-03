from datetime import datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from config.constants import IST
from config.database import async_session_factory

app = FastAPI(title="Trading Bot Dashboard", version="1.0.0")

STATIC_DIR = Path(__file__).parent.parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    html_path = STATIC_DIR / "index.html"
    if html_path.exists():
        return HTMLResponse(content=html_path.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>Trading Bot Dashboard</h1><p>static/index.html not found</p>")


@app.get("/api/positions")
async def get_positions() -> list[dict]:
    async with async_session_factory() as session:
        result = await session.execute(
            text("""
                SELECT symbol, direction, quantity, price, fill_price, status, created_at
                FROM orders
                WHERE status = 'COMPLETE'
                ORDER BY created_at DESC
                LIMIT 50
            """)
        )
        rows = result.fetchall()
    return [
        {
            "symbol": r[0],
            "direction": r[1],
            "quantity": r[2],
            "price": str(r[3]),
            "fill_price": str(r[4]) if r[4] else None,
            "status": r[5],
            "created_at": r[6].isoformat() if r[6] else None,
        }
        for r in rows
    ]


@app.get("/api/trades")
async def get_recent_trades() -> list[dict]:
    async with async_session_factory() as session:
        result = await session.execute(
            text("""
                SELECT id, symbol, direction, quantity, price, fill_price, status, created_at, updated_at
                FROM orders
                ORDER BY created_at DESC
                LIMIT 100
            """)
        )
        rows = result.fetchall()
    return [
        {
            "id": r[0],
            "symbol": r[1],
            "direction": r[2],
            "quantity": r[3],
            "price": str(r[4]),
            "fill_price": str(r[5]) if r[5] else None,
            "status": r[6],
            "created_at": r[7].isoformat() if r[7] else None,
            "updated_at": r[8].isoformat() if r[8] else None,
        }
        for r in rows
    ]


@app.get("/api/signals")
async def get_recent_signals() -> list[dict]:
    async with async_session_factory() as session:
        result = await session.execute(
            text("""
                SELECT id, strategy_name, symbol, direction, price, timestamp
                FROM signals
                ORDER BY timestamp DESC
                LIMIT 50
            """)
        )
        rows = result.fetchall()
    return [
        {
            "id": r[0],
            "strategy": r[1],
            "symbol": r[2],
            "direction": r[3],
            "price": str(r[4]),
            "timestamp": r[5].isoformat() if r[5] else None,
        }
        for r in rows
    ]


@app.get("/api/audit")
async def get_audit_log() -> list[dict]:
    async with async_session_factory() as session:
        result = await session.execute(
            text("""
                SELECT id, event_type, event_data, timestamp
                FROM audit_log
                ORDER BY timestamp DESC
                LIMIT 50
            """)
        )
        rows = result.fetchall()
    return [
        {
            "id": r[0],
            "event_type": r[1],
            "event_data": r[2],
            "timestamp": r[3].isoformat() if r[3] else None,
        }
        for r in rows
    ]


@app.get("/api/health")
async def health() -> dict:
    return {
        "status": "ok",
        "timestamp": datetime.now(tz=IST).isoformat(),
        "mode": "paper",
    }
