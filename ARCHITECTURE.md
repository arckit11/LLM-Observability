# LLM Observatory — Architecture Decision Records (ADRs)

## Overview

This document records the major architectural decisions made in the LLM Observatory platform, their rationale, alternatives considered, and tradeoffs.

---

## ADR-001: Async-First Backend Architecture

**Status**: Adopted  
**Date**: 2024  
**Context**: Need to handle high-volume trace ingestion without blocking

### Decision
Use **async/await throughout** the backend:
- FastAPI + Uvicorn (async ASGI)
- SQLAlchemy 2.0 with asyncio driver
- asyncpg for PostgreSQL (not psycopg2)
- redis.asyncio for Redis (not redis-py)
- Consumer loop: `async def consume_forever()`

### Rationale
1. **Throughput**: Can handle 1000+ concurrent requests/producer tasks without thread overhead
2. **Cost**: Single-threaded process model = lower memory footprint
3. **Modern Python**: Async/await is mainstream since 3.5+
4. **Ecosystem**: FastAPI, SQLAlchemy 2.0, asyncpg all mature

### Alternatives Considered
| Alternative | Pros | Cons |
|-------------|------|------|
| **Sync** (threads) | Simpler code, wider library support | Memory overhead (1 thread = 1-2MB), GIL contention |
| **Gevent** | Monkey-patching, older projects | Less predictable, not mainstream |
| **Trio** | Structured concurrency | Smaller ecosystem than asyncio |

### Tradeoffs
- ✅ **High throughput, low latency**
- ⚠️ Debugging async code is harder (stacktraces less clear)
- ⚠️ All dependencies must be async-compatible

---

## ADR-002: Redis Streams for Trace Queue

**Status**: Adopted  
**Date**: 2024  
**Context**: Need decoupled producer/consumer, resilient to backend crashes

### Decision
Use **Redis Streams** (`XADD`, `XREADGROUP`) as the trace queue instead of:
- Direct PostgreSQL inserts
- Simple Redis lists
- RabbitMQ / Apache Kafka

### Rationale
1. **Consumer Groups**: Built-in replay on worker restart (consumer group offset tracking)
2. **Persistence**: AOF backup via `redis-server --appendonly yes`
3. **Ordering**: Guarantees monotonic stream order (important for latency analysis)
4. **Simplicity**: No external broker setup required
5. **Cost**: Runs in memory, no separate infrastructure

### Alternatives Considered
| Alternative | Pros | Cons |
|-------------|------|------|
| **Direct PostgreSQL** | Single database | No decoupling; DB becomes bottleneck under load |
| **Redis Lists** | Simple, fast | No consumer groups; message loss on crash |
| **RabbitMQ** | Battle-tested, durable | Extra infra; overkill for v0.1 |
| **Kafka** | Horizontal scaling | Overkill; requires ZooKeeper/Kraft setup |
| **SQS** | AWS-native, durable | Vendor lock-in; not self-hostable |

### Tradeoffs
- ✅ **Fast, resilient, self-hosted**
- ✅ **Consumer groups enable replay**
- ⚠️ Redis persistence requires monitoring (not as strong as Kafka)
- ⚠️ Single Redis instance = single point of failure (but this is a design constraint for v0.1)

---

## ADR-003: Batch Processing in Consumer

**Status**: Adopted  
**Date**: 2024  
**Context**: Avoid database thrashing; reduce connection overhead

### Decision
**Batch 100 spans per database commit** in consumer:
- Read up to 100 messages from Redis stream
- Bulk insert all 100 rows in one SQL transaction
- Run alert engine for each span
- Commit batch atomically
- Acknowledge batch to consumer group

### Rationale
1. **Throughput**: 100 individual inserts = 100 round trips; batch = 1 round trip
2. **Connection pooling**: Fewer active connections
3. **Transaction overhead**: Amortized across batch
4. **Alert latency**: Per-span alerts still run immediately

### Alternatives Considered
| Batch Size | Latency | Throughput | Memory |
|------------|---------|-----------|--------|
| 1 | Low | ~100 spans/sec | Low |
| **100** | **~1s delay** | **~10k spans/sec** | **~1MB** |
| 1000 | ~10s delay | ~100k spans/sec | ~10MB |
| 10000 | ~100s delay | Too slow (risk cascade fail) | ~100MB |

### Code Impact
```python
BATCH_SIZE = 100
BLOCK_MS = 1000  # 1-second block if no messages

messages = await r.xreadgroup(GROUP, CONSUMER, {STREAM: ">"}, count=BATCH_SIZE, block=BLOCK_MS)
# Collect batch, bulk insert, commit once
```

### Tradeoffs
- ✅ **10x throughput vs single-row inserts**
- ⚠️ **~1 second latency** (spans not immediately queryable)
- ⚠️ Need to tune batch size if load changes

---

## ADR-004: SQLAlchemy 2.0 ORM with Raw SQL Fallback

**Status**: Adopted  
**Date**: 2024  
**Context**: Need type safety and composability for queries, but also complex analytics

### Decision
**Primary**: SQLAlchemy 2.0 ORM (models, relationships, type hints)  
**Fallback**: Raw SQL for PostgreSQL-specific features (e.g., `percentile_cont`)

### Rationale
1. **Type Safety**: Pydantic + SQLAlchemy = caught errors at dev time
2. **Maintainability**: ORM queries are readable; less SQL syntax errors
3. **Migrations**: If we ever add/remove columns, one place to change
4. **Performance**: For analytics queries, raw SQL is clearer and sometimes faster

### Query Examples

#### ORM (preferred for simple queries)
```python
# Cost summary by model
stmt = select(
    TraceSpan.model,
    func.sum(TraceSpan.cost_usd).label("total"),
    func.count(TraceSpan.id).label("calls"),
).group_by(TraceSpan.model)

result = await db.execute(stmt)
```

#### Raw SQL (for PostgreSQL-specific features)
```python
# P95 latency percentile (PostgreSQL WITHIN GROUP syntax)
query = text("""
    SELECT 
        model,
        percentile_cont(0.95) WITHIN GROUP (ORDER BY latency_ms) AS p95
    FROM trace_spans
    GROUP BY model
""")
result = await db.execute(query)
```

### Tradeoffs
- ✅ **Best of both worlds**: Type safety + advanced queries
- ✅ **Readable code**
- ⚠️ **Mixed approach** = more patterns to learn
- ⚠️ **Raw SQL not type-checked** (risk of typos)

---

## ADR-005: Decorator-Based SDK Instrumentation

**Status**: Adopted  
**Date**: 2024  
**Context**: Minimize code changes for users; make observability frictionless

### Decision
Provide **`@observe` decorator** for automatic instrumentation instead of:
- Explicit SDK method calls
- Middleware / monkey-patching
- Wrapper functions

### Rationale
1. **Minimal Code Changes**: 0 changes to existing LLM logic
2. **Opt-In**: Only decorate functions you want to observe
3. **Composability**: Works with async/sync, context managers, etc.
4. **Signal Intent**: Decorator clearly marks observed functions

### Example (Before vs After)

**Before** (no observability):
```python
def chat(question: str):
    return openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": question}],
    )
```

**After** (with @observe):
```python
from llmobs import observe

@observe(name="chat", tags={"env": "prod"})
def chat(question: str):
    return openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": question}],
    )
```

### Alternatives Considered
| Alternative | Pros | Cons |
|-------------|------|------|
| **Explicit calls** | Clear intent, granular control | Verbose; easy to forget calls |
| **Middleware** | Automatic for all calls | Hard to customize; couples to framework |
| **Monkey-patching** | Automatic | Fragile; breaks with updates |
| **@observe (chosen)** | Minimal code, clear intent | Need to apply decorator |

### Tradeoffs
- ✅ **Minimal friction for users**
- ✅ **Explicit + optional**
- ⚠️ Requires decorating each function (not fully automatic)

---

## ADR-006: Context-Propagated Trace IDs

**Status**: Adopted  
**Date**: 2024  
**Context**: Support multi-step LLM chains with single trace ID

### Decision
Use **Python `contextvars.ContextVar`** to propagate trace and session IDs across decorated functions, avoiding explicit parameter passing.

### Rationale
1. **Implicit Propagation**: Child function calls inherit parent trace ID automatically
2. **No Parameter Pollution**: Don't pass trace_id through function signatures
3. **Standard Library**: `contextvars` built-in, stable
4. **Async-Safe**: Isolated per async task

### Usage
```python
from llmobs import observe, trace

@observe(name="intent-extractor")
def extract_intent(msg):
    # trace_id inherited from context
    return openai.chat.completions.create(...)

@observe(name="response-gen")
def generate(intent):
    # trace_id inherited from context
    return openai.chat.completions.create(...)

# Both calls grouped under same trace_id
with trace(session_id="user-123"):
    intent = extract_intent("hello")
    response = generate(intent)
```

### Alternatives Considered
| Alternative | Pros | Cons |
|-------------|------|------|
| **ContextVar (chosen)** | Implicit, async-safe | Slightly less explicit |
| **threading.local** | Simpler | Not async-safe; breaks with asyncio |
| **Explicit params** | Clear, predictable | Verbose; pollutes function signatures |
| **Thread-local storage** | Works for threads | Deprecated; doesn't support asyncio |

### Tradeoffs
- ✅ **Clean, async-safe code**
- ✅ **Implicit propagation**
- ⚠️ **Magic** — less obvious where trace ID comes from (but documented)

---

## ADR-007: PostgreSQL for Persistence

**Status**: Adopted  
**Date**: 2024  
**Context**: Need durable, queryable trace storage

### Decision
Use **PostgreSQL 16** (not SQLite, Cassandra, Elasticsearch, etc.)

### Rationale
1. **ACID Guarantees**: Durable transactions; consistent state after crash
2. **Query Flexibility**: Arbitrary SQL for analytics (percentiles, aggregations)
3. **Indexing**: B-tree, partial, composite indexes for fast lookups
4. **Operational Simplicity**: Single process, no cluster management
5. **Cost**: Self-hostable, no per-query pricing
6. **Scalability**: Handles millions of rows with good performance

### Query Examples
```sql
-- Percentile latency (PostgreSQL-specific)
SELECT percentile_cont(0.95) WITHIN GROUP (ORDER BY latency_ms)
FROM trace_spans;

-- Window functions for trending
SELECT model, latency_ms, ROW_NUMBER() OVER (PARTITION BY model ORDER BY created_at)
FROM trace_spans;

-- Full-text search on prompts (future)
SELECT * FROM trace_spans WHERE prompt @@ to_tsquery('english', 'error');
```

### Alternatives Considered
| Alternative | Pros | Cons |
|-------------|------|------|
| **SQLite** | Simple, embedded | Single-writer; slow analytics; not horizontally scalable |
| **Cassandra** | Horizontal scale | Complex; overkill for v0.1; limited analytics |
| **Elasticsearch** | Full-text search, fast | Bloated; expensive; not primary DB |
| **DynamoDB** | AWS-native | Vendor lock-in; expensive at scale; limited queries |
| **PostgreSQL (chosen)** | Flexible, powerful, simple | Vertical scaling limit (~10TB on single node) |

### Tradeoffs
- ✅ **Powerful query language**
- ✅ **Reliable, ACID**
- ✅ **Self-hostable**
- ⚠️ **Single-server model** (horizontal scaling requires read replicas / sharding)
- ⚠️ **Not ideal for time-series** (but sufficient for v0.1)

---

## ADR-008: Next.js Frontend for Dashboard

**Status**: Adopted  
**Date**: 2024  
**Context**: Need fast, responsive monitoring UI

### Decision
Use **Next.js 16** + **React 19** instead of:
- Plain React SPA
- Vue
- Svelte
- Server-rendered alternatives

### Rationale
1. **Full-Stack JS**: Can share types/models between backend and frontend
2. **Fast**: Built-in code splitting, image optimization, ISR
3. **SEO**: Server-side rendering available (though not critical for dashboard)
4. **DX**: Hot module reloading, fast feedback loop
5. **Ecosystem**: Rich component libraries (Shadcn, Recharts, etc.)

### Charting
Use **Recharts** (React wrapper around D3):
- Line charts for timeseries (cost trend, latency trends)
- Pie/donut charts for categorical breakdown (top models)
- Responsive by default

### Alternatives Considered
| Alternative | Pros | Cons |
|-------------|------|------|
| **Plain React SPA** | Lightweight, simple | No SSR; build tooling needed |
| **Vue** | Approachable | Smaller ecosystem than React |
| **Svelte** | Fast, compact | Smaller community |
| **Next.js (chosen)** | Full-stack, fast | Large bundle; requires Node runtime |

### Tradeoffs
- ✅ **Developer experience**
- ✅ **Fast, responsive UI**
- ✅ **Built-in optimizations**
- ⚠️ **Larger bundle size**
- ⚠️ **Node.js required** (can't run on edge only)

---

## ADR-009: Model-Agnostic Pricing

**Status**: Adopted  
**Date**: 2024  
**Context**: Support multiple LLM providers (OpenAI, Anthropic, Google, OSS)

### Decision
**Maintain hardcoded pricing table** (not fetched from APIs):
- 14 models: OpenAI, Anthropic, Google, open-source
- **Fallback to $0 cost** for unknown models (never break observability)
- Support prefix matching for version variants

### Rationale
1. **Observability Never Breaks App**: Returning $0 is better than raising exception
2. **Offline Operation**: Don't depend on external price-feed APIs
3. **Predictability**: Prices change rarely; updated quarterly in code
4. **Simplicity**: No extra dependencies or network calls

### Code Example
```python
PRICING = {
    "gpt-4o": (2.50e-6, 10.00e-6),  # input, output per token
    "claude-3-5-sonnet": (3.00e-6, 15.00e-6),
}

def calculate_cost(model, tokens_in, tokens_out):
    price = _resolve_pricing(model)
    if price is None:
        return 0.0  # Never break
    input_cost, output_cost = price
    return (tokens_in * input_cost) + (tokens_out * output_cost)
```

### Alternatives Considered
| Alternative | Pros | Cons |
|-------------|------|------|
| **Hardcoded (chosen)** | Predictable, offline | Manual updates, incomplete coverage |
| **Fetch from API** | Always current | External dependency; latency; failure risk |
| **Config file** | Customizable | Need validation, schema versioning |
| **User-provided** | Maximum flexibility | Error-prone; UI/API complexity |

### Tradeoffs
- ✅ **Never breaks on unknown model**
- ✅ **Offline, fast**
- ✅ **Simple**
- ⚠️ **Manually maintained pricing table**
- ⚠️ **May be incorrect for new models**

---

## ADR-010: Alert Rules (No User Configuration)

**Status**: Adopted  
**Date**: 2024  
**Context**: Keep MVP simple; focus on useful defaults

### Decision
**Hardcode 3 alert rules**:
1. **High-cost session** (> $0.50)
2. **Error spike** (> 10% in 5 min)
3. **High latency** (> 5000ms per span)

No user customization in v0.1.

### Rationale
1. **MVP Simplicity**: Avoid alert config complexity
2. **Sensible Defaults**: Rules chosen empirically for typical LLM workloads
3. **Fast MVP**: Ship observability value quickly
4. **Future Extensibility**: Easy to make configurable in v0.2

### Thresholds Chosen
- **$0.50** = Typical session spend (1-3 API calls at standard rates)
- **10%** = Significant error spike (worth alerting on)
- **5000ms** = P99 latency for most models; unusual slowdown

### Alternatives Considered
| Alternative | Pros | Cons |
|-------------|------|------|
| **Hardcoded (chosen)** | Simple, MVP-focused | Inflexible; may not suit all users |
| **Env var config** | Customizable | Added complexity; need validation |
| **API endpoint** | Full flexibility | UI complexity; stateful alerts |
| **ML-based** | Adaptive thresholds | Overkill for v0.1 |

### Future Migration Path
```python
# v0.2: Make configurable
ALERT_RULES = {
    "high_cost_session": os.getenv("ALERT_HIGH_COST", 0.50),
    "error_spike_threshold": os.getenv("ALERT_ERROR_PCT", 0.10),
    "high_latency_ms": os.getenv("ALERT_LATENCY", 5000),
}
```

---

## ADR-011: CORS Open to All Origins

**Status**: Accepted (Temporary)  
**Date**: 2024  
**Context**: Allow local dashboard + external clients during development

### Decision
Configure CORS to allow all origins:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Rationale
1. **Development**: Dashboard on localhost:3000, backend on localhost:8000
2. **Self-Hosted**: Not exposed to internet (firewall assumed)
3. **Simplicity**: No auth yet, so CORS is minor security concern

### ⚠️ Production Risk
**DO NOT USE IN PRODUCTION** without:
1. Authentication (API key, OAuth)
2. Rate limiting
3. Authorization checks
4. CORS restricted to known origins

### Future: Production Config
```python
# v0.2+: Restrict to dashboard domain + API keys
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://dashboard.myorg.com"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT"],
    allow_headers=["Authorization"],
)
```

---

## Summary Table

| ADR | Decision | Status | Risk |
|-----|----------|--------|------|
| ADR-001 | Async-first backend | Adopted | Medium (debugging complexity) |
| ADR-002 | Redis Streams queue | Adopted | Low (well-tested pattern) |
| ADR-003 | Batch 100 spans | Adopted | Low (tunable) |
| ADR-004 | SQLAlchemy 2.0 + raw SQL | Adopted | Low (standard practice) |
| ADR-005 | @observe decorator | Adopted | Low (popular pattern) |
| ADR-006 | ContextVar trace IDs | Adopted | Low (standard library) |
| ADR-007 | PostgreSQL | Adopted | Low (proven) |
| ADR-008 | Next.js dashboard | Adopted | Medium (bundle size) |
| ADR-009 | Hardcoded pricing | Adopted | Medium (needs manual updates) |
| ADR-010 | Hardcoded alert rules | Adopted | Medium (not customizable) |
| ADR-011 | Open CORS (dev only) | Accepted | **HIGH** (auth required before prod) |

---

## Next: Production Hardening

See [PROJECT_REVIEW.md](./PROJECT_REVIEW.md#-deployment-checklist) for the deployment checklist before taking LLM Observatory to production.
