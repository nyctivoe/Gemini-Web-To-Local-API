import asyncio
import httpx
from loguru import logger

from app.providers.base import BaseProvider
from app.config import OpenAIConfig


class _ChatSession:
    """Stores message history for a stateful chat session."""
    def __init__(self, model: str, name: str):
        self.model = model
        self.name = name
        self.messages: list[dict] = []


class OpenAIProvider(BaseProvider):
    """
    Provider that calls any OpenAI-compatible API.
    Works with: OpenAI, Ollama, LM Studio, Together, Groq, etc.
    """

    def __init__(self):
        self._client: httpx.AsyncClient | None = None
        self._sessions: dict[str, _ChatSession] = {}
        self._lock = asyncio.Lock()

    async def init(self) -> None:
        if not OpenAIConfig.is_configured():
            raise RuntimeError(
                "OpenAI-compatible provider not configured. "
                "Set base_url in [OpenAI] section of config.conf."
            )
        headers = {"Content-Type": "application/json"}
        if OpenAIConfig.api_key:
            headers["Authorization"] = f"Bearer {OpenAIConfig.api_key}"

        self._client = httpx.AsyncClient(
            base_url=OpenAIConfig.base_url.rstrip("/"),
            headers=headers,
            timeout=120.0,
        )
        logger.info(
            f"OpenAIProvider initialized → {OpenAIConfig.base_url} "
            f"(default model: {OpenAIConfig.default_model})"
        )

    async def generate(self, message: str, model: str) -> str:
        if not self._client:
            raise RuntimeError("OpenAIProvider not initialized")

        model = model or OpenAIConfig.default_model

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": message}],
        }

        resp = await self._client.post("/v1/chat/completions", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    async def chat(self, message: str, model: str, session_id: str = "default") -> str:
        if not self._client:
            raise RuntimeError("OpenAIProvider not initialized")

        model = model or OpenAIConfig.default_model

        async with self._lock:
            existing = self._sessions.get(session_id)
            if existing is None or existing.model != model:
                self._sessions[session_id] = _ChatSession(model, session_id)

            session = self._sessions[session_id]
            session.messages.append({"role": "user", "content": message})

            payload = {
                "model": model,
                "messages": session.messages,
            }

            resp = await self._client.post("/v1/chat/completions", json=payload)
            resp.raise_for_status()
            data = resp.json()

            reply = data["choices"][0]["message"]["content"]
            session.messages.append({"role": "assistant", "content": reply})

        return reply

    async def generate_raw(self, payload: dict) -> dict:
        """
        Pass-through: forward a full OpenAI-format request body
        directly to the upstream API and return the raw response.
        """
        if not self._client:
            raise RuntimeError("OpenAIProvider not initialized")

        if not payload.get("model"):
            payload["model"] = OpenAIConfig.default_model

        resp = await self._client.post("/v1/chat/completions", json=payload)
        resp.raise_for_status()
        return resp.json()

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
