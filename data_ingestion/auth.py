import json

import pyotp
import redis.asyncio as redis
import structlog
from SmartApi import SmartConnect

from config.settings import settings

logger = structlog.get_logger(__name__)

SESSION_KEY = "smartapi:session"
SESSION_TTL_SECONDS = 6 * 60 * 60  # 6 hours


class SmartAPIAuth:
    def __init__(self) -> None:
        self._redis: redis.Redis | None = None
        self._smart_connect: SmartConnect | None = None

    async def _get_redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
        return self._redis

    def _generate_totp(self) -> str:
        totp = pyotp.TOTP(settings.SMARTAPI_TOTP_SECRET)
        return totp.now()

    async def login(self) -> dict:
        r = await self._get_redis()
        cached = await r.get(SESSION_KEY)
        if cached:
            session_data = json.loads(cached)
            logger.info("smartapi_session_restored", client_id=settings.SMARTAPI_CLIENT_ID)
            return session_data

        self._smart_connect = SmartConnect(api_key=settings.SMARTAPI_API_KEY)
        totp_token = self._generate_totp()

        session_data = self._smart_connect.generateSession(
            clientCode=settings.SMARTAPI_CLIENT_ID,
            password=settings.SMARTAPI_PASSWORD,
            totp=totp_token,
        )

        if not session_data or session_data.get("status") is False:
            error_msg = session_data.get("message", "Unknown error") if session_data else "No response"
            logger.error("smartapi_login_failed", error=error_msg)
            raise ConnectionError(f"SmartAPI login failed: {error_msg}")

        await r.set(SESSION_KEY, json.dumps(session_data), ex=SESSION_TTL_SECONDS)
        logger.info("smartapi_login_success", client_id=settings.SMARTAPI_CLIENT_ID)
        return session_data

    async def get_session(self) -> dict:
        r = await self._get_redis()
        cached = await r.get(SESSION_KEY)
        if cached:
            return json.loads(cached)
        return await self.login()

    async def get_auth_token(self) -> str:
        session = await self.get_session()
        return session["data"]["jwtToken"]

    async def get_feed_token(self) -> str:
        session = await self.get_session()
        return session["data"]["feedToken"]

    async def get_smart_connect(self) -> SmartConnect:
        if self._smart_connect is None:
            await self.login()
        assert self._smart_connect is not None
        return self._smart_connect

    async def logout(self) -> None:
        r = await self._get_redis()
        await r.delete(SESSION_KEY)
        if self._smart_connect:
            try:
                self._smart_connect.terminateSession(settings.SMARTAPI_CLIENT_ID)
            except Exception:
                logger.warning("smartapi_logout_error", exc_info=True)
        logger.info("smartapi_session_cleared")

    async def close(self) -> None:
        if self._redis:
            await self._redis.close()
