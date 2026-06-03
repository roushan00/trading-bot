import asyncio
import json
from typing import Callable

import structlog
from SmartApi.smartWebSocketV2 import SmartWebSocketV2

from config.settings import settings
from data_ingestion.auth import SmartAPIAuth
from data_ingestion.normalizer import Tick

logger = structlog.get_logger(__name__)

EXCHANGE_NSE = 1
EXCHANGE_BSE = 3
EXCHANGE_NFO = 2

MODE_LTP = 1
MODE_QUOTE = 2
MODE_SNAP_QUOTE = 3


class FeedHandler:
    def __init__(
        self,
        auth: SmartAPIAuth,
        tokens: list[dict],
        on_tick: Callable[[Tick], None] | None = None,
        mode: int = MODE_SNAP_QUOTE,
    ) -> None:
        self._auth = auth
        self._tokens = tokens
        self._on_tick = on_tick
        self._mode = mode
        self._ws: SmartWebSocketV2 | None = None
        self._running = False
        self._reconnect_delay = 1.0
        self._max_reconnect_delay = 60.0
        self._token_map: dict[str, str] = {}

    def _build_token_list(self) -> list[dict]:
        token_list = []
        for t in self._tokens:
            exchange = t.get("exchange", EXCHANGE_NSE)
            token = str(t["token"])
            self._token_map[token] = t["symbol"]
            token_list.append({
                "exchangeType": exchange,
                "tokens": [token],
            })
        return token_list

    async def connect(self) -> None:
        self._running = True
        while self._running:
            try:
                await self._connect_once()
            except Exception:
                logger.error("websocket_error", exc_info=True)
                if not self._running:
                    break
                logger.info(
                    "websocket_reconnecting",
                    delay=self._reconnect_delay,
                )
                await asyncio.sleep(self._reconnect_delay)
                self._reconnect_delay = min(
                    self._reconnect_delay * 2,
                    self._max_reconnect_delay,
                )

    async def _connect_once(self) -> None:
        auth_token = await self._auth.get_auth_token()
        feed_token = await self._auth.get_feed_token()
        client_id = settings.SMARTAPI_CLIENT_ID
        api_key = settings.SMARTAPI_API_KEY

        self._ws = SmartWebSocketV2(
            auth_token, api_key, client_id, feed_token
        )

        token_list = self._build_token_list()

        def on_data(ws: SmartWebSocketV2, message: str) -> None:
            try:
                data = json.loads(message) if isinstance(message, str) else message
                token = str(data.get("token", ""))
                if token in self._token_map:
                    data["name"] = self._token_map[token]
                tick = Tick.from_smartapi(data)
                if self._on_tick:
                    self._on_tick(tick)
            except Exception:
                logger.error("tick_parse_error", exc_info=True, raw=str(message)[:200])

        def on_open(ws: SmartWebSocketV2) -> None:
            logger.info("websocket_connected")
            self._reconnect_delay = 1.0
            ws.subscribe("abc123", self._mode, token_list)

        def on_error(ws: SmartWebSocketV2, error: str) -> None:
            logger.error("websocket_on_error", error=str(error)[:200])

        def on_close(ws: SmartWebSocketV2, close_status: int, close_msg: str) -> None:
            logger.warning("websocket_closed", status=close_status, message=close_msg)

        self._ws.on_data = on_data
        self._ws.on_open = on_open
        self._ws.on_error = on_error
        self._ws.on_close = on_close

        logger.info("websocket_connecting", tokens=len(self._tokens))
        self._ws.connect()

    async def disconnect(self) -> None:
        self._running = False
        if self._ws:
            try:
                self._ws.close_connection()
            except Exception:
                logger.warning("websocket_close_error", exc_info=True)
        logger.info("websocket_disconnected")
