# LLM Observatory

**Open-source LLM observability platform.** Drop two lines into your code and get full visibility into every LLM call — costs, latency, prompts, responses, and errors.

Think [LangSmith](https://smith.langchain.com/), but open source, pip-installable, and yours.

---

## What You Get

| Feature | Description |
|---------|-------------|
| **`@observe` decorator** | Wrap any LLM call — zero code changes to your existing logic |
| **`trace()` context manager** | Group multi-step chains under one trace ID |
| **Cost tracking** | Per-call, per-model, per-session cost breakdown |
| **Latency analytics** | P50/P95/P99 percentiles, trend analysis |
| **Trace explorer** | Full prompt/response replay for every call |
| **Alerting** | Cost thresholds, error spikes, latency anomalies |
| **Multi-model** | OpenAI, Anthropic, Google, open-source models |

## Quick Start

### 1. Start the Platform

```bash
git clone https://github.com/yourname/llm-observatory.git
cd llm-observatory
docker compose up -d
```

This starts PostgreSQL, Redis, the backend API, and the dashboard.

### 2. Install the SDK

```bash
pip install llmobs
```

Or for local development:

```bash
cd sdk && pip install -e .
```

### 3. Add Two Lines to Your Code

```python
# Before: zero observability
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Summarise this document..."}]
)

# After: full observability
from llmobs import observe

@observe(name="document-summariser", tags={"feature": "doc-upload"})
def summarise(text):
    return client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": f"Summarise: {text}"}]
    )
```

### 4. Open the Dashboard

Navigate to **http://localhost:3000** and see:

- 💰 Total spend for the day
- 🏎️ Which model is slowest
- 🔥 Which session cost the most
- 🔄 Full prompt and response replay for any call

---

## Multi-Step Traces

Group related LLM calls under one trace:

```python
from llmobs import observe, trace

@observe(name="intent-extractor")
def extract_intent(message):
    return client.chat.completions.create(...)

@observe(name="response-generator")
def generate_response(intent, products):
    return client.chat.completions.create(...)

# Both calls appear together in the trace explorer
with trace(session_id="user-42", name="product-search-flow"):
    intent   = extract_intent("I need running shoes under $100")
    response = generate_response(intent, ["Nike Pegasus", "Adidas Ride"])
```

---

## Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Your App      │     │              │     │              │     │              │
│                 │────▸│ Redis Stream  │────▸│   Backend    │────▸│  PostgreSQL  │
│  @observe(...)  │     │              │     │  (consumer)  │     │              │
└─────────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
                                                    │
                                                    ▼
                                             ┌──────────────┐
                                             │  Dashboard   │
                                             │  (Next.js)   │
                                             └──────────────┘
```

**SDK** → writes trace events to a **Redis Stream** (non-blocking, fire-and-forget)
**Backend** → consumes the stream, stores in **PostgreSQL**, exposes REST API
**Dashboard** → queries the API and renders charts, tables, trace explorer

---

## Project Structure

```
llm-observatory/
├── sdk/                          ← The pip-installable package
│   ├── llmobs/
│   │   ├── __init__.py           ← exports @observe, trace()
│   │   ├── decorator.py          ← @observe implementation
│   │   ├── context.py            ← trace context management
│   │   ├── queue.py              ← async Redis Streams writer
│   │   ├── cost.py               ← token → cost calculator
│   │   └── schema.py             ← Pydantic models for trace events
│   └── pyproject.toml
│
├── backend/
│   ├── app/
│   │   ├── main.py               ← FastAPI app
│   │   ├── consumer.py           ← Redis Streams consumer loop
│   │   ├── alerting.py           ← cost/error/latency alert engine
│   │   ├── routers/
│   │   │   ├── traces.py         ← GET /traces, GET /traces/{id}
│   │   │   ├── cost.py           ← GET /cost/summary, /cost/timeseries
│   │   │   ├── latency.py        ← GET /latency/percentiles
│   │   │   └── alerts.py         ← GET /alerts, POST /alerts/resolve
│   │   └── db/
│   │       ├── models.py         ← SQLAlchemy ORM models
│   │       └── session.py        ← async session factory
│   └── Dockerfile
│
├── dashboard/                    ← Next.js dashboard
│   ├── src/
│   │   ├── app/                  ← App Router pages
│   │   ├── components/           ← Reusable UI components
│   │   └── lib/                  ← API client
│   └── Dockerfile
│
├── docker-compose.yml            ← Full stack orchestration
├── scripts/
│   └── seed_data.py              ← Generate synthetic demo data
└── examples/
    ├── basic_usage.py
    ├── langchain_example.py
    └── multi_agent_example.py
```

---

## Demo Data

Populate the dashboard with realistic synthetic data:

```bash
# Install redis client
pip install redis

# Generate 2000 traces (≈5000 spans)
python scripts/seed_data.py

# Or generate more
python scripts/seed_data.py --count 10000
```

---

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/stats/overview` | Dashboard overview metrics |
| `GET /api/traces` | Paginated trace list with filters |
| `GET /api/traces/{trace_id}` | All spans for a trace |
| `GET /api/traces/sessions` | Unique sessions with stats |
| `GET /api/cost/summary` | Per-model cost breakdown |
| `GET /api/cost/timeseries` | Hourly/daily cost trends |
| `GET /api/latency/percentiles` | P50/P95/P99 per model |
| `GET /api/latency/timeseries` | Latency trends over time |
| `GET /api/alerts` | Active and resolved alerts |
| `POST /api/alerts/{id}/resolve` | Resolve an alert |

---

## Supported Models

| Provider | Models | Pricing |
|----------|--------|---------|
| OpenAI | gpt-4o, gpt-4o-mini, gpt-4-turbo, gpt-3.5-turbo | ✅ |
| Anthropic | claude-3.5-sonnet, claude-3-haiku, claude-3-opus | ✅ |
| Google | gemini-1.5-pro, gemini-1.5-flash, gemini-2.0-flash | ✅ |
| Open Source | llama3, mixtral | Free ($0) |

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LLMOBS_REDIS_HOST` | `localhost` | Redis host for the SDK |
| `LLMOBS_REDIS_PORT` | `6379` | Redis port |
| `DATABASE_URL` | `postgresql+asyncpg://...` | PostgreSQL connection string |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend API URL for dashboard |

---

## License

MIT
