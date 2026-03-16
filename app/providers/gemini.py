import asyncio
from loguru import logger
from gemini_webapi import GeminiClient

from app.providers.base import BaseProvider
from app.config import GeminiCookies, ProxyConfig


class _ChatSession:
    """Wraps a gemini-webapi ChatSession with metadata."""
    def __init__(self, session, model: str, name: str):
        self.session = session
        self.model = model
        self.name = name


class GeminiProvider(BaseProvider):
    def __init__(self):
        self._client: GeminiClient | None = None
        self._sessions: dict[str, _ChatSession] = {}
        self._lock = asyncio.Lock()

    async def init(self) -> None:
        if not GeminiCookies.is_configured():
            raise RuntimeError(
                "Gemini cookies not configured. "
                "Set PSID and PSIDTS in config.conf."
            )
        proxy = ProxyConfig.url or None
        self._client = GeminiClient(
            cookies=GeminiCookies.as_dict(),
            proxy=proxy,
        )
        await self._client.init(timeout=30, auto_close=False, auto_refresh=True)
        logger.info("GeminiProvider initialized")

    async def generate(self, message: str, model: str) -> str:
        if not self._client:
            raise RuntimeError("GeminiProvider not initialized")
        response = await self._client.generate_content(message, model=model)
        return response.text

    async def chat(self, message: str, model: str, session_id: str = "default") -> str:
        if not self._client:
            raise RuntimeError("GeminiProvider not initialized")
        async with self._lock:
            existing = self._sessions.get(session_id)
            # Create new session or reset if model changed
            if existing is None or existing.model != model:
                chat = self._client.start_chat(model=model)
                self._sessions[session_id] = _ChatSession(chat, model, session_id)
            response = await self._sessions[session_id].session.send_message(message)
        return response.text

    def list_sessions(self) -> list[dict]:
        return [
            {"session_id": sid, "name": s.name, "model": s.model}
            for sid, s in self._sessions.items()
        ]

    def rename_session(self, session_id: str, new_name: str) -> bool:
        if session_id not in self._sessions:
            return False
        self._sessions[session_id].name = new_name
        return True

    def delete_session(self, session_id: str) -> bool:
        if session_id not in self._sessions:
            return False
        del self._sessions[session_id]
        return True
