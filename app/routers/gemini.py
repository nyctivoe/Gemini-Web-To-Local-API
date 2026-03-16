import json
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from loguru import logger
from pydantic import BaseModel

from app.schemas import GeminiRequest, GeminiResponse

router = APIRouter(prefix="/gemini", tags=["gemini"])


def _get_provider(request: Request):
    provider = getattr(request.app.state, "gemini_provider", None)
    if provider is None:
        raise HTTPException(status_code=503, detail="Gemini provider not available")
    return provider


@router.post("")
async def gemini_generate(req: GeminiRequest, request: Request):
    """Stateless single-turn generation."""
    provider = _get_provider(request)

    if req.stream:
        async def event_generator():
            try:
                async for chunk in provider.generate_stream(req.message, req.model):
                    yield f"data: {json.dumps({'chunk': chunk})}\n\n"
            except Exception as e:
                logger.error(f"Gemini generate stream error: {e}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    try:
        text = await provider.generate(req.message, req.model)
        return GeminiResponse(response=text)
    except Exception as e:
        logger.error(f"Gemini generate error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat")
async def gemini_chat(req: GeminiRequest, request: Request):
    """Stateful multi-turn chat (session persists across requests)."""
    provider = _get_provider(request)

    if req.stream:
        async def event_generator():
            try:
                async for chunk in provider.chat_stream(req.message, req.model, req.session_id):
                    yield f"data: {json.dumps({'chunk': chunk})}\n\n"
            except Exception as e:
                logger.error(f"Gemini chat stream error: {e}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    try:
        text = await provider.chat(req.message, req.model, req.session_id)
        return GeminiResponse(response=text)
    except Exception as e:
        logger.error(f"Gemini chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions")
async def list_sessions(request: Request):
    """List all active chat sessions."""
    provider = _get_provider(request)
    return {"sessions": provider.list_sessions()}


class RenameRequest(BaseModel):
    name: str


@router.patch("/sessions/{session_id}")
async def rename_session(session_id: str, req: RenameRequest, request: Request):
    """Rename a chat session."""
    provider = _get_provider(request)
    if not provider.rename_session(session_id, req.name):
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    return {"status": "renamed", "session_id": session_id, "name": req.name}


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, request: Request):
    """Delete a chat session."""
    provider = _get_provider(request)
    if not provider.delete_session(session_id):
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    return {"status": "deleted", "session_id": session_id}
