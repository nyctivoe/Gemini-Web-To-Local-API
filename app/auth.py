from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import AuthConfig

_scheme = HTTPBearer(auto_error=False)


async def verify_api_key(
    credentials: HTTPAuthorizationCredentials | None = Security(_scheme),
) -> None:
    """
    FastAPI dependency that checks Authorization: Bearer <key>.
    If API_KEY is not set in .env, all requests are allowed.
    """
    if not AuthConfig.is_enabled():
        return

    if credentials is None or credentials.credentials != AuthConfig.api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
