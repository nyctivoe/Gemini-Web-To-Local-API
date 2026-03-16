import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")


def _get(key: str, fallback: str = "") -> str:
    return os.getenv(key, fallback).strip()


class ServerConfig:
    host: str = _get("SERVER_HOST", "0.0.0.0")
    port: int = int(_get("SERVER_PORT", "6969"))


class GeminiCookies:
    PSID: str = _get("GEMINI_PSID")
    PSIDTS: str = _get("GEMINI_PSIDTS")

    @classmethod
    def as_dict(cls) -> dict[str, str]:
        return {
            "__Secure-1PSID": cls.PSID,
            "__Secure-1PSIDTS": cls.PSIDTS,
        }

    @classmethod
    def is_configured(cls) -> bool:
        return bool(cls.PSID and cls.PSIDTS)


class ProxyConfig:
    url: str = _get("PROXY_URL")
