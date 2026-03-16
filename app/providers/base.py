from abc import ABC, abstractmethod
from collections.abc import AsyncIterator


class BaseProvider(ABC):
    """
    Abstract base class for all AI providers.
    Implement this to add a new provider (e.g. Claude, ChatGPT).
    """

    @abstractmethod
    async def init(self) -> None:
        """Initialize the provider (auth, session setup, etc.)."""
        ...

    @abstractmethod
    async def generate(self, message: str, model: str) -> str:
        """Stateless single-turn generation."""
        ...

    @abstractmethod
    async def generate_stream(self, message: str, model: str) -> AsyncIterator[str]:
        """Stateless generation, yields text chunks."""
        ...
        yield  # pragma: no cover — makes this a valid abstract async generator

    @abstractmethod
    async def chat(self, message: str, model: str, session_id: str = "default") -> str:
        """Stateful multi-turn chat (session persists across calls)."""
        ...

    @abstractmethod
    async def chat_stream(self, message: str, model: str, session_id: str = "default") -> AsyncIterator[str]:
        """Stateful chat, yields text chunks."""
        ...
        yield  # pragma: no cover

    def list_sessions(self) -> list[dict]:
        return []

    def rename_session(self, session_id: str, new_name: str) -> bool:
        return False

    def delete_session(self, session_id: str) -> bool:
        return False
