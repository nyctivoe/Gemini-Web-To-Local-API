import json
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from loguru import logger

from app.auth import verify_api_key
from app.schemas import OpenAIChatRequest, OpenAITool

router = APIRouter(prefix="/v1", tags=["openai-compat"], dependencies=[Depends(verify_api_key)])


def _get_provider(request: Request):
    provider = getattr(request.app.state, "gemini_provider", None)
    if provider is None:
        raise HTTPException(status_code=503, detail="Gemini provider not available")
    return provider


def _build_tool_system_prompt(tools: list[OpenAITool], tool_choice: str | dict | None) -> str:
    """Build a system prompt that describes available tools to Gemini."""
    tool_defs = []
    for tool in tools:
        fn = tool.function
        tool_defs.append(json.dumps({
            "name": fn.name,
            "description": fn.description,
            "parameters": fn.parameters,
        }, indent=2))

    tools_json = "\n".join(tool_defs)

    # Determine if we should force tool usage
    force = tool_choice not in (None, "none", "auto")

    prompt = f"""## TOOL USE INSTRUCTIONS

You are a function-calling AI. You have access to the following tools:

{tools_json}

### RULES — YOU MUST FOLLOW THESE EXACTLY:

1. When the user's request can be answered by a tool, you MUST call the tool. Do NOT answer from your own knowledge.
2. To call a tool, your ENTIRE response must be ONLY the following JSON — no other text before or after:

{{"tool_call": {{"name": "function_name", "arguments": {{"param": "value"}}}}}}

3. Do NOT wrap the JSON in markdown code fences. Do NOT add any explanation, greeting, or commentary.
4. Only respond with plain text if NONE of the available tools are relevant to the user's request.
5. The arguments must match the parameter names and types defined in the tool schema."""

    if force:
        prompt += "\n6. You MUST call a tool in this response. Do NOT respond with plain text."

    return prompt


def _format_messages(req: OpenAIChatRequest) -> str:
    """Convert OpenAI messages array into a prompt string for Gemini."""
    parts = []

    # Inject tool definitions as system context
    if req.tools:
        parts.append(f"system: {_build_tool_system_prompt(req.tools, req.tool_choice)}")

    for m in req.messages:
        if m.role == "tool":
            # Format tool results so Gemini understands them
            parts.append(f"tool_result (id={m.tool_call_id}): {m.content}")
        elif m.role == "assistant" and m.tool_calls:
            # Re-serialize previous assistant tool calls
            calls = json.dumps(m.tool_calls)
            parts.append(f"assistant: [tool calls: {calls}]")
        else:
            parts.append(f"{m.role}: {m.content or ''}")

    return "\n".join(parts)


def _parse_tool_calls(text: str) -> list[dict] | None:
    """Try to parse Gemini's response as tool call(s). Returns None if it's plain text."""
    stripped = text.strip()

    # Strip markdown code fences if present
    if stripped.startswith("```"):
        lines = stripped.split("\n")
        # Remove first line (```json or ```) and last line (```)
        if lines[-1].strip() == "```":
            lines = lines[1:-1]
        else:
            lines = lines[1:]
        stripped = "\n".join(lines).strip()

    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        return None

    # Single tool call: {"tool_call": {"name": ..., "arguments": ...}}
    if isinstance(parsed, dict) and "tool_call" in parsed:
        call = parsed["tool_call"]
        return [
            {
                "id": f"call_{uuid.uuid4().hex[:12]}",
                "type": "function",
                "function": {
                    "name": call["name"],
                    "arguments": json.dumps(call.get("arguments", {})),
                },
            }
        ]

    # Multiple tool calls: [{"tool_call": {...}}, ...]
    if isinstance(parsed, list) and all(isinstance(c, dict) and "tool_call" in c for c in parsed):
        return [
            {
                "id": f"call_{uuid.uuid4().hex[:12]}",
                "type": "function",
                "function": {
                    "name": c["tool_call"]["name"],
                    "arguments": json.dumps(c["tool_call"].get("arguments", {})),
                },
            }
            for c in parsed
        ]

    return None


@router.post("/chat/completions")
async def openai_chat_completions(req: OpenAIChatRequest, request: Request):
    """OpenAI-compatible chat completions endpoint with tool calling and streaming support."""
    provider = _get_provider(request)

    prompt = _format_messages(req)

    # Tool calls need full response to parse JSON — force non-streaming
    if req.stream and not req.tools:
        async def event_generator():
            try:
                async for text_chunk in provider.generate_stream(prompt, req.model):
                    chunk = {
                        "object": "chat.completion.chunk",
                        "model": req.model,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {"content": text_chunk},
                                "finish_reason": None,
                            }
                        ],
                    }
                    yield f"data: {json.dumps(chunk)}\n\n"
            except Exception as e:
                logger.error(f"OpenAI-compat stream error: {e}")
                error_chunk = {"error": {"message": str(e)}}
                yield f"data: {json.dumps(error_chunk)}\n\n"

            # Final chunk with finish_reason
            final = {
                "object": "chat.completion.chunk",
                "model": req.model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {},
                        "finish_reason": "stop",
                    }
                ],
            }
            yield f"data: {json.dumps(final)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    # Non-streaming path (also used when tools are provided)
    try:
        text = await provider.generate(prompt, req.model)
    except Exception as e:
        logger.error(f"OpenAI-compat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    # Check if tools were provided and response looks like a tool call
    tool_calls = None
    if req.tools:
        tool_calls = _parse_tool_calls(text)

    if tool_calls:
        return {
            "object": "chat.completion",
            "model": req.model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": tool_calls,
                    },
                    "finish_reason": "tool_calls",
                }
            ],
        }

    return {
        "object": "chat.completion",
        "model": req.model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": text},
                "finish_reason": "stop",
            }
        ],
    }
