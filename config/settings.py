from decimal import Decimal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    APP_NAME: str = "trading-bot"
    APP_ENV: str = "development"
    DEBUG: bool = True
    PAPER_TRADING_MODE: bool = True

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://trading_bot:trading_bot_dev@localhost:5432/trading_bot"
    DATABASE_URL_SYNC: str = "postgresql://trading_bot:trading_bot_dev@localhost:5432/trading_bot"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Angel One SmartAPI
    SMARTAPI_API_KEY: str = ""
    SMARTAPI_CLIENT_ID: str = ""
    SMARTAPI_PASSWORD: str = ""
    SMARTAPI_TOTP_SECRET: str = ""

    # Risk Management
    MAX_DAILY_LOSS_PCT: Decimal = Field(default=Decimal("2.0"))
    MAX_DRAWDOWN_PCT: Decimal = Field(default=Decimal("10.0"))
    MAX_POSITION_PCT: Decimal = Field(default=Decimal("5.0"))
    RISK_PER_TRADE_PCT: Decimal = Field(default=Decimal("1.0"))
    INITIAL_CAPITAL: Decimal = Field(default=Decimal("100000"))

    # Logging
    LOG_LEVEL: str = "INFO"

    # Email Alerts
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    ALERT_RECIPIENT: str = ""


settings = Settings()
