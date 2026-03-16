from pydantic import BaseModel


class GeminiRequest(BaseModel):
    message: str
    model: str = "gemini-3.1-pro"
    session_id: str = "default"


class GeminiResponse(BaseModel):
    response: str


class OpenAIFunction(BaseModel):
    name: str
    description: str = ""
    parameters: dict = {}


class OpenAITool(BaseModel):
    type: str = "function"
    function: OpenAIFunction


class OpenAIMessage(BaseModel):
    role: str
    content: str | None = None
    tool_calls: list[dict] | None = None
    tool_call_id: str | None = None


class OpenAIChatRequest(BaseModel):
    messages: list[OpenAIMessage]
    model: str = "gemini-3.1-pro"
    stream: bool = False
    tools: list[OpenAITool] | None = None
    tool_choice: str | dict | None = None


class OpenAIChatResponse(BaseModel):
    choices: list[dict]
    model: str
    object: str = "chat.completion"
