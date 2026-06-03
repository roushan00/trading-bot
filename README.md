
# AI Trading Bot

> Automated trading bot for Indian financial markets (NSE/BSE) — Path A Learning Path v1.0

## Status

🚧 **Pre-development.** Documentation phase complete. Implementation has not yet started.

## What This Is

A rule-based automated trading system for the Indian markets that:

- Ingests live market data via Angel One SmartAPI
- Runs 3 rule-based strategies (EMA Crossover, RSI Reversal, Opening Range Breakout)
- Applies hard risk controls (kill switch, daily loss limit, max drawdown, position size cap)
- Paper trades for a minimum of 8 weeks before any live deployment is considered

## What This Is Not (Yet)

- ❌ Not a real-money trading system — v1.0 is paper trading only
- ❌ No ML or Reinforcement Learning — deferred to v2.0
- ❌ No web frontend — minimal HTML page in v1.0
- ❌ Not financial advice — this is a personal project for learning

## Documentation

| Document | Purpose |
|---|---|
| `CLAUDE.md` | Project rules and conventions (read first if using Claude Code) |
| `docs/01_PRD.docx` | Product Requirements Document |
| `docs/02_HLD_LLD.docx` | High-Level and Low-Level Design |
| `docs/04_Dev_Plan_PathA.docx` | 12-week phase-by-phase development plan |

## Quick Start (Once Code Exists)

```bash
# 1. Clone and enter
git clone <repo-url> && cd trading-bot

# 2. Set up Python environment
python -m venv venv
source venv/bin/activate            # Linux/Mac
# venv\Scripts\activate              # Windows
pip install -r requirements.txt

# 3. Start infrastructure
docker-compose up -d

# 4. Configure environment
cp .env.example .env
# Edit .env with your SmartAPI credentials

# 5. Run database migrations
alembic upgrade head

# 6. Run tests
pytest tests/

# 7. Start in paper mode
python main.py
```

## Development Roadmap

| Phase | Duration | Status |
|---|---|---|
| Phase 1 — Foundation & Infrastructure | 2 weeks | ⬜ Not started |
| Phase 2 — Data Ingestion Pipeline | 3 weeks | ⬜ Not started |
| Phase 3 — Strategies + Backtesting | 2 weeks | ⬜ Not started |
| Phase 4 — Risk Management & Kill Switch | 2 weeks | ⬜ Not started |
| Phase 5 — Paper Trading + Dashboard | 3 weeks + 8 weeks paper trade | ⬜ Not started |

**Total: 12 weeks of dev + 8 weeks of paper trading before any go/no-go decision on v2.0.**

## Safety Disclaimer

This is an educational project. Algorithmic trading carries significant financial risk. Past performance in backtesting does not guarantee future results. Never trade real money without:

- Thorough backtesting on out-of-sample data
- Minimum 8 weeks of profitable paper trading
- A working kill switch you have tested
- An amount you can afford to lose entirely

## Legal

This project routes orders through a SEBI-registered broker (Angel One). It does not constitute or provide financial advice.

## License

Private. Not for redistribution.
