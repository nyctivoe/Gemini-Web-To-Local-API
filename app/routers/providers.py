from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(prefix="/providers", tags=["providers"])


@router.get("")
async def list_providers(request: Request):
    """List all available providers and which one is active."""
    available = list(request.app.state.providers.keys())
    active = request.app.state.active_provider_name
    return {"active": active, "available": available}


class SwitchRequest(BaseModel):
    provider: str


@router.post("/switch")
async def switch_provider(req: SwitchRequest, request: Request):
    """Switch the active provider."""
    if req.provider not in request.app.state.providers:
        available = list(request.app.state.providers.keys())
        raise HTTPException(
            status_code=400,
            detail=f"Provider '{req.provider}' not available. Available: {available}",
        )
    request.app.state.active_provider_name = req.provider
    return {"status": "switched", "active": req.provider}
