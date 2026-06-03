from config.settings import Settings


def test_settings_load_defaults() -> None:
    s = Settings(
        DATABASE_URL="postgresql+asyncpg://test:test@localhost/test",
        DATABASE_URL_SYNC="postgresql://test:test@localhost/test",
    )
    assert s.APP_NAME == "trading-bot"
    assert s.PAPER_TRADING_MODE is True
    assert s.APP_ENV == "development"


def test_paper_trading_mode_is_default() -> None:
    s = Settings(
        DATABASE_URL="postgresql+asyncpg://test:test@localhost/test",
        DATABASE_URL_SYNC="postgresql://test:test@localhost/test",
    )
    assert s.PAPER_TRADING_MODE is True, "Paper trading must be default in v1.0"
