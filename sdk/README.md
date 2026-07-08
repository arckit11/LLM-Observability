# llmobs — LLM Observability SDK

Lightweight, zero-config observability for LLM applications. Add one decorator and get traces, token counts, cost estimates, and latency metrics streamed to Redis — without ever blocking your app.

## Features

- **`@observe` decorator** — wraps any LLM call (sync or async) and captures traces automatically
- **`trace` context manager** — groups related spans under a single trace ID
- **Auto-detection** — extracts tokens, model, and response from OpenAI & Anthropic response objects
- **Token-to-cost calculator** — covers GPT-4o, Claude 3.5, Gemini 2.0, Llama 3, Mixtral, and more
- **Non-blocking writes** — fire-and-forget Redis Streams delivery on daemon threads
- **Silent failures** — observability never crashes your application

## Installation

```bash
pip install llmobs
```

Or install from source:

```bash
git clone https://github.com/your-org/llmobs.git
cd llmobs/sdk
pip install -e ".[dev]"
```

### Requirements

- Python ≥ 3.9
- Redis server (for trace delivery)
- `pydantic ≥ 2.0`
- `redis ≥ 5.0`

## Quick Start

### 1. Observe a single function

```python
from llmobs import observe
import openai

client = openai.OpenAI()

@observe(tags={"team": "search"})
def ask(question: str):
    return client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": question}],
    )

answer = ask("What is LLM observability?")
```

Every call to `ask()` automatically records a `TraceEvent` containing model name, prompt, response text, token counts, estimated cost, latency, and any errors.

### 2. Group spans with `trace`

```python
from llmobs import observe, trace

@observe()
def embed(text: str):
    return openai.embeddings.create(model="text-embedding-3-small", input=text)

@observe()
def generate(context: str, question: str):
    return openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": f"Context: {context}"},
            {"role": "user", "content": question},
        ],
    )

with trace(name="rag-pipeline", session_id="user-42"):
    emb = embed("some document text")
    answer = generate("retrieved context", "Summarise this")
```

Both spans share the same `trace_id` and `session_id`.

### 3. Async support

```python
import asyncio
from llmobs import observe

@observe(name="async-chat")
async def async_ask(question: str):
    return await async_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": question}],
    )

asyncio.run(async_ask("Hello!"))
```

### 4. Configure Redis connection

By default the SDK connects to `localhost:6379`. Override via environment variables:

```bash
export LLMOBS_REDIS_HOST=redis.internal
export LLMOBS_REDIS_PORT=6380
export LLMOBS_REDIS_PASSWORD=secret
```

Or programmatically:

```python
from llmobs import ObsClient

client = ObsClient(redis_host="redis.internal", redis_port=6380)
```

### 5. Cost estimation

```python
from llmobs import calculate_cost

cost = calculate_cost("gpt-4o", tokens_in=500, tokens_out=150)
print(f"${cost:.6f}")  # $0.002750
```

## API Reference

### `@observe(name=None, *, session_id=None, tags=None)`

Decorator factory that instruments a function.

| Parameter    | Type            | Description                                      |
|-------------|-----------------|--------------------------------------------------|
| `name`      | `str \| None`   | Span name (defaults to function `__name__`)      |
| `session_id`| `str \| None`   | Explicit session ID for this span                |
| `tags`      | `dict \| None`  | Arbitrary metadata attached to the trace event   |

### `trace(*, name="trace", session_id=None, trace_id=None)`

Context manager (sync & async) that groups child spans under one trace.

| Parameter    | Type            | Description                                      |
|-------------|-----------------|--------------------------------------------------|
| `name`      | `str`           | Human-readable trace label                       |
| `session_id`| `str \| None`   | Session ID propagated to child spans             |
| `trace_id`  | `str \| None`   | Explicit trace ID (auto-generated if omitted)    |

### `TraceEvent`

Pydantic v2 model representing a single observed span.

| Field        | Type              | Description                        |
|-------------|-------------------|------------------------------------|
| `span_id`   | `str`             | Unique span identifier             |
| `trace_id`  | `str`             | Shared trace identifier            |
| `session_id`| `str \| None`     | Optional session grouping          |
| `name`      | `str`             | Span label                         |
| `model`     | `str`             | LLM model identifier               |
| `prompt`    | `str`             | Input prompt / messages            |
| `response`  | `str`             | Model response text                |
| `tokens_in` | `int`             | Input token count                  |
| `tokens_out`| `int`             | Output token count                 |
| `cost_usd`  | `float`           | Estimated cost in USD              |
| `latency_ms`| `int`             | Call latency in milliseconds       |
| `error`     | `str \| None`     | Error message (if failed)          |
| `tags`      | `dict`            | Arbitrary metadata                 |
| `timestamp` | `datetime`        | UTC timestamp                      |

### `calculate_cost(model, tokens_in, tokens_out) -> float`

Estimate USD cost for an LLM call. Supports fuzzy model matching (e.g. `"gpt-4o-2024-08-06"` matches `"gpt-4o"`).

**Supported models:** `gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo`, `gpt-3.5-turbo`, `claude-3-5-sonnet`, `claude-3-haiku`, `claude-3-opus`, `gemini-1.5-pro`, `gemini-1.5-flash`, `gemini-2.0-flash`, `llama3`, `mixtral`

### `ObsClient`

Configuration helper that sets Redis connection parameters.

```python
client = ObsClient(
    redis_host="redis.internal",
    redis_port=6380,
    redis_password="secret",
    default_tags={"env": "production"},
)
```

## Architecture

```
┌──────────────┐    ┌──────────────┐    ┌─────────────────┐
│  Your App    │───▶│  @observe    │───▶│  Redis Streams   │
│  (LLM calls) │    │  decorator   │    │  llmobs:traces   │
└──────────────┘    └──────┬───────┘    └────────┬────────┘
                           │                     │
                    ┌──────▼───────┐    ┌────────▼────────┐
                    │  TraceEvent  │    │  Ingest Worker   │
                    │  (Pydantic)  │    │  (downstream)    │
                    └──────────────┘    └─────────────────┘
```

Events flow through a daemon thread to Redis Streams, ensuring your application is never blocked by observability overhead.

## License

MIT
