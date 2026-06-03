import asyncio
import sys

from sqlalchemy import text

from config.database import async_session_factory, engine


async def show_status() -> None:
    async with async_session_factory() as session:
        # Recent trades
        trades = await session.execute(
            text("""
                SELECT id, symbol, direction, quantity, price, fill_price, status, created_at
                FROM orders
                ORDER BY created_at DESC
                LIMIT 10
            """)
        )
        trade_rows = trades.fetchall()

        # Open positions (net)
        positions = await session.execute(
            text("""
                SELECT symbol,
                       SUM(CASE WHEN direction = 'BUY' THEN quantity ELSE -quantity END) as net_qty,
                       AVG(fill_price) as avg_price
                FROM orders
                WHERE status = 'COMPLETE'
                GROUP BY symbol
                HAVING SUM(CASE WHEN direction = 'BUY' THEN quantity ELSE -quantity END) != 0
            """)
        )
        pos_rows = positions.fetchall()

        # Daily P&L (today's completed orders)
        pnl = await session.execute(
            text("""
                SELECT COUNT(*), COALESCE(SUM(
                    CASE WHEN direction = 'SELL' THEN fill_price * quantity
                         ELSE -fill_price * quantity END
                ), 0) as net
                FROM orders
                WHERE status = 'COMPLETE'
                  AND created_at::date = CURRENT_DATE
            """)
        )
        pnl_row = pnl.fetchone()

    print("=" * 60)
    print("  TRADING BOT STATUS  [PAPER MODE]")
    print("=" * 60)

    print("\n  OPEN POSITIONS")
    print("-" * 60)
    if pos_rows:
        print(f"  {'Symbol':<15} {'Net Qty':>10} {'Avg Price':>12}")
        print(f"  {'─'*15} {'─'*10} {'─'*12}")
        for r in pos_rows:
            print(f"  {r[0]:<15} {r[1]:>10} {r[2]:>12.2f}" if r[2] else f"  {r[0]:<15} {r[1]:>10} {'N/A':>12}")
    else:
        print("  No open positions")

    print(f"\n  TODAY'S SUMMARY")
    print("-" * 60)
    if pnl_row:
        print(f"  Trades today: {pnl_row[0]}")
        print(f"  Net flow:     {pnl_row[1]:,.2f}")

    print(f"\n  RECENT TRADES")
    print("-" * 60)
    if trade_rows:
        print(f"  {'ID':>5} {'Symbol':<12} {'Dir':<5} {'Qty':>5} {'Price':>10} {'Fill':>10} {'Status':<10} {'Time'}")
        print(f"  {'─'*5} {'─'*12} {'─'*5} {'─'*5} {'─'*10} {'─'*10} {'─'*10} {'─'*20}")
        for r in trade_rows:
            fill = f"{r[5]:.2f}" if r[5] else "N/A"
            time_str = r[7].strftime("%H:%M:%S") if r[7] else "N/A"
            print(f"  {r[0]:>5} {r[1]:<12} {r[2]:<5} {r[3]:>5} {r[4]:>10.2f} {fill:>10} {r[5+1]:<10} {time_str}")
    else:
        print("  No trades yet")

    print("=" * 60)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(show_status())
