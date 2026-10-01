from datetime import time
from decimal import Decimal
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")

MARKET_OPEN = time(9, 15, tzinfo=IST)
MARKET_CLOSE = time(15, 30, tzinfo=IST)

PRE_MARKET_OPEN = time(9, 0, tzinfo=IST)
POST_MARKET_CLOSE = time(15, 40, tzinfo=IST)

WEBSOCKET_START = time(9, 14, tzinfo=IST)
WEBSOCKET_STOP = time(15, 31, tzinfo=IST)

# NSE holidays for 2026 (update annually)
# Source: NSE circular
NSE_HOLIDAYS_2026 = [
    "2026-01-26",  # Republic Day
    "2026-02-17",  # Mahashivratri
    "2026-03-10",  # Holi
    "2026-03-30",  # Id-ul-Fitr (Ramzan)
    "2026-04-02",  # Ram Navami
    "2026-04-03",  # Good Friday
    "2026-04-14",  # Dr. Ambedkar Jayanti
    "2026-05-01",  # Maharashtra Day
    "2026-05-25",  # Buddha Purnima
    "2026-06-06",  # Id-ul-Zuha (Bakri Id)
    "2026-07-06",  # Muharram
    "2026-08-15",  # Independence Day
    "2026-08-18",  # Parsi New Year
    "2026-09-04",  # Milad-un-Nabi
    "2026-10-02",  # Mahatma Gandhi Jayanti
    "2026-10-20",  # Dussehra
    "2026-11-09",  # Diwali (Laxmi Pujan)
    "2026-11-10",  # Diwali (Balipratipada)
    "2026-11-30",  # Guru Nanak Jayanti
    "2026-12-25",  # Christmas
]

# Supported timeframes for candle aggregation
TIMEFRAMES = ["1min", "5min", "15min", "1hr", "1D"]

# Brokerage & fees (as fraction, not percent)
BROKERAGE_RATE = Decimal("0.0003")       # 0.03%
STT_RATE = Decimal("0.00025")            # 0.025% on sell side
SLIPPAGE_RATE = Decimal("0.0005")        # 0.05% default slippage
