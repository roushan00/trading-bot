# Claude Code Kickoff Prompts

Use these prompts in order when you launch Claude Code in this directory.

> **⚠️ IMPORTANT:** Before launching Claude Code, make sure you have:
> 1. Python 3.11+ installed (`python --version`)
> 2. Docker + docker-compose installed (`docker --version`, `docker-compose --version`)
> 3. Git installed and configured (`git config user.name`, `git config user.email`)
> 4. Your Angel One SmartAPI credentials ready (API key, client ID, password, TOTP secret)
> 5. Opened a terminal in the `trading-bot/` directory
> 6. Launched Claude Code with: `claude`

---

## Prompt 1 — Project Orientation (use this FIRST)

```
Read CLAUDE.md in full. Then summarise back to me in 5 bullet points:
1. What this project is
2. What scope is in v1.0 vs deferred to v2.0
3. The 5 phases and their durations
4. The hard rules I must never violate
5. The current status and the next concrete action

Do not write any code yet. Do not read the .docx files yet.
```

**What to expect:** A clear, structured summary. If the summary is vague, missing details, or hallucinates features not in CLAUDE.md, stop and clarify before proceeding. This is your sanity check that Claude Code has properly absorbed the context.

---

## Prompt 2 — Phase 1, Task 1.1 (Repo & Folder Structure)

```
We are now starting Phase 1, Task 1.1: Repository & folder structure.

Open docs/04_Dev_Plan_PathA.docx and read ONLY the Phase 1 section
to understand the task and its evaluation criteria.

Then:
1. Create the full folder structure described in CLAUDE.md
2. Add __init__.py to every Python package folder
3. Create a comprehensive .gitignore for Python projects
   (include venv/, __pycache__/, .env, *.pyc, .pytest_cache/,
    .mypy_cache/, ml_pipeline/models/, *.pkl, .DS_Store)
4. Initialise git: git init, git add ., git commit -m "phase 1.1: initial folder structure"

Then stop and show me the resulting tree. Do not proceed to task 1.2.
```

---

## Prompt 3 — Phase 1, Task 1.2 (Python venv + requirements.txt)

```
Phase 1, Task 1.2: Python virtual environment.

Create requirements.txt with these exact versions:
- fastapi==0.111.0
- uvicorn[standard]==0.29.0
- pydantic-settings==2.2.1
- sqlalchemy==2.0.30
- asyncpg==0.29.0
- alembic==1.13.1
- redis==5.0.4
- smartapi-python==1.3.9
- pandas==2.2.2
- numpy==1.26.4
- pandas-ta==0.3.14b
- backtrader==1.9.78.123
- celery==5.4.0
- apscheduler==3.10.4
- python-dotenv==1.0.1
- pyotp==2.9.0
- httpx==0.27.0
- websockets==12.0
- structlog==24.1.0
- pytest==8.2.0
- pytest-asyncio==0.23.6
- pytest-mock==3.14.0
- ruff==0.4.4
- black==24.4.2
- mypy==1.10.0

Then provide me the exact terminal commands to:
1. Create a Python 3.11 venv
2. Activate it
3. Install requirements

DO NOT run those commands yourself — I will run them manually.
After I confirm installation succeeded, commit with message
"phase 1.2: python environment".
```

**Why manual install:** Claude Code will sometimes silently fail on pip install or use the wrong Python. Better to run it yourself the first time.

---

## Prompt 4 — Phase 1, Task 1.3 (Docker Compose)

```
Phase 1, Task 1.3: Docker Compose setup.

Create docker-compose.yml with:
- PostgreSQL 15 (port 5432, named volume postgres_data, healthcheck pg_isready)
- Redis 7-alpine (port 6379, healthcheck redis-cli ping)
- Network: trading-bot-net (bridge)
- Both services restart: unless-stopped
- Use environment variables for credentials (POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB)

Also create .env.example with placeholders for:
- SmartAPI credentials (SMARTAPI_KEY, SMARTAPI_CLIENT_ID, SMARTAPI_PASSWORD, SMARTAPI_TOTP_SECRET)
- Database (POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, DATABASE_URL)
- Redis (REDIS_URL)
- Risk params (MAX_POSITION_PCT=0.05, DAILY_LOSS_LIMIT_PCT=0.02, MAX_DRAWDOWN_PCT=0.10)
- App (PAPER_TRADING_MODE=true, LOG_LEVEL=INFO, TIMEZONE=Asia/Kolkata)

Provide the command to start containers, but DO NOT run it yourself.

After I confirm both containers are healthy via docker-compose ps,
commit with "phase 1.3: docker compose setup".
```

---

## How to Continue from Here

After Prompt 4, just keep going through the dev plan task by task. Use the same pattern:

```
Phase X, Task X.Y: <task name>.

[Specific instructions for this task]

Run the evaluation criteria for this task. Report pass/fail.
If pass, commit with "phase X.Y: <task name>" and stop.
If fail, explain what failed.
```

---

## Useful Slash Commands in Claude Code

| Command | Purpose |
|---|---|
| `/clear` | Clear the conversation (start fresh, keeps CLAUDE.md context) |
| `/cost` | See how many tokens you've used in this session |
| `/help` | Show all commands |
| `/exit` | Exit Claude Code |

---

## Anti-Patterns to Avoid

| ❌ Don't do this | ✅ Do this instead |
|---|---|
| "Build the entire Phase 1" | "Do task 1.1 only, then stop" |
| "Skip the tests for now" | "Write the test, then make it pass" |
| "Just commit everything" | "Commit per task with descriptive message" |
| "Make it work somehow" | "Show me what's failing and let's fix it together" |
| Ignoring failed eval criteria | Stop, fix, re-evaluate before moving on |

---

## When Claude Code Goes Off The Rails

Signs you should stop and reset:
- It's editing files outside the task scope
- It's adding dependencies you didn't approve
- It's writing tests that test nothing real
- It's repeating the same fix without success
- It says "I'll just simplify this" and removes safety code

**Recovery:** `git reset --hard HEAD` and start the task over with a clearer prompt.

---

## End of Each Day Checklist

- [ ] All today's tasks have passing tests
- [ ] All changes committed with phase-tagged messages
- [ ] Updated "Current Status" in CLAUDE.md to reflect progress
- [ ] No `.env` accidentally committed (check `git log --all -- .env`)
- [ ] No API keys in code (`grep -r "SMARTAPI_KEY=" --include="*.py"` should return nothing)
