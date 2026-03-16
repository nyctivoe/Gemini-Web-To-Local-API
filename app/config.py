import configparser
import os
from pathlib import Path

_CONFIG_PATH = Path(__file__).parent.parent / "config.conf"

_config = configparser.ConfigParser()
_config.read(_CONFIG_PATH, encoding="utf-8")


def _get(section: str, key: str, fallback: str = "") -> str:
    return _config.get(section, key, fallback=fallback).strip()


class ServerConfig:
    host: str = _get("Server", "host", "0.0.0.0")
    port: int = int(_get("Server", "port", "6969"))


class GeminiCookies:
    PSID: str = _get("Cookies", "PSID")
    PSIDTS: str = _get("Cookies", "PSIDTS")

    @classmethod
    def as_dict(cls) -> dict[str, str]:
        return {
            "__Secure-1PSID": cls.PSID,
            "__Secure-1PSIDTS": cls.PSIDTS,
        }

    @classmethod
    def is_configured(cls) -> bool:
        return bool(cls.PSID and cls.PSIDTS)


class OpenAIConfig:
    base_url: str = _get("OpenAI", "base_url")
    api_key: str = _get("OpenAI", "api_key")
    default_model: str = _get("OpenAI", "default_model")

    @classmethod
    def is_configured(cls) -> bool:
        return bool(cls.base_url)


class ProviderConfig:
    active: str = _get("Provider", "active", "gemini")


class ProxyConfig:
    url: str = _get("Proxy", "url")
