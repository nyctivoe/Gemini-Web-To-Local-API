# Gemini Local API

A local REST API server that proxies Google Gemini's web interface through browser cookies, using your existing session.

## Setup

### 1. Install dependencies

```bash
uv venv
uv pip install -r requirements.txt
```

### 2. Configure cookies

Copy the example config:

```bash
cp example.config.conf config.conf
```

Get your cookies from Chrome:

1. Go to [gemini.google.com](https://gemini.google.com) (make sure you're logged in)
2. Press `F12` → **Application** tab → **Cookies** → `https://gemini.google.com`
3. Copy `__Secure-1PSID` → paste as `PSID` in `config.conf`
4. Copy `__Secure-1PSIDTS` → paste as `PSIDTS` in `config.conf`

### 3. Run

```bash
python main.py
```

Server starts at `http://localhost:6969`. Interactive docs at `http://localhost:6969/docs`.

## Endpoints

### `POST /gemini` — Stateless generation

Single prompt, no memory between requests.

```json
{"message": "What is Python?", "model": "gemini-3.1-pro"}
```

Response:

```json
{"response": "Python is a programming language..."}
```

### `POST /gemini/chat` — Stateful chat

Maintains conversation history across requests, like the Gemini web app.

```json
{"message": "My name is Alex", "model": "gemini-3.1-pro", "session_id": "default"}
```

Follow-up (same `session_id` remembers context):

```json
{"message": "What is my name?", "session_id": "default"}
```

### `POST /v1/chat/completions` — OpenAI-compatible

Drop-in replacement for OpenAI's chat completions format. Supports tool definitions.

```json
{
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello!"}
  ],
  "model": "gemini-3.1-pro"
}
```

### Session Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/gemini/sessions` | List all active chat sessions |
| `PATCH` | `/gemini/sessions/{id}` | Rename a session (`{"name": "new name"}`) |
| `DELETE` | `/gemini/sessions/{id}` | Delete a session |

## Available Models

| Model | Description |
|-------|-------------|
| `gemini-3.1-pro` | Most capable (default) |
| `gemini-3.0-flash` | Fast |
| `gemini-3.0-flash-thinking` | Flash with chain-of-thought |

## Project Structure

```
Gemini_LocalAPI/
├── main.py                    # Entry point
├── config.conf                # Your cookies (gitignored)
├── example.config.conf        # Config template
├── requirements.txt
└── app/
    ├── config.py              # Config loader
    ├── core.py                # FastAPI app factory
    ├── schemas.py             # Request/response models
    ├── providers/
    │   ├── base.py            # Abstract provider interface
    │   └── gemini.py          # Gemini provider
    └── routers/
        ├── gemini.py          # /gemini routes
        └── openai_compat.py   # /v1/chat/completions route
```

## Adding New Providers

The project uses an abstract `BaseProvider` class. To add a new AI provider:

1. Create `app/providers/your_provider.py` implementing `BaseProvider`
2. Add a router in `app/routers/`
3. Register it in `app/core.py`

No changes to existing code required.

## Notes

- Cookies expire periodically. If requests start failing, grab fresh cookies from Chrome.
- This uses the free Gemini web interface, not the paid API.
- Automated access may violate Google's Terms of Service. Use at your own risk.
