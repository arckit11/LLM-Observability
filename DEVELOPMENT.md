# LLM Observatory — Development & Testing Guide

## 🏃 Quick Start (Local Development)

### Prerequisites
```bash
# Check Python version (need ≥3.9)
python --version

# Check Node version (need ≥18)
node --version

# Check Docker is running
docker --version
```

### 1. Clone & Setup
```bash
cd /home/griffith/Projects/LLM\ Observability\ Platform

# Copy environment template
cp .env.example .env

# Edit .env with your OpenAI key (optional for examples)
# OPENAI_API_KEY=sk-...
```

### 2. Start Infrastructure
```bash
docker compose up -d

# Verify all services are running
docker compose ps
# Expected: postgres, redis, backend, dashboard all "healthy"

# Check backend is alive
curl http://localhost:8000/health
# Expected: {"status": "healthy", "service": "llm-observability-backend"}

# Check PostgreSQL
docker compose exec postgres psql -U postgres -d llmobs -c "SELECT COUNT(*) FROM trace_spans;"
```

### 3. Install SDK (Development Mode)
```bash
cd sdk
pip install -e ".[dev]"
cd ..
```

### 4. Run Example
```bash
# Basic example (requires OPENAI_API_KEY set)
python examples/basic_usage.py

# Mock demo (no API keys needed)
python examples/mock_demo.py

# Then visit http://localhost:3000 and explore the dashboard
```

### 5. Develop

#### Backend
```bash
cd backend

# Install dev dependencies
pip install -e ".[dev]"

# Run tests (when available)
pytest

# Watch logs
docker compose logs -f backend
```

#### Dashboard
```bash
cd dashboard

npm install
npm run dev  # Starts on http://localhost:3000 (dev mode)
npm run build && npm run start  # Production-like
```

#### SDK
```bash
cd sdk

pip install -e ".[dev]"
pytest
mypy llmobs/
ruff check llmobs/
```

---

## 🧪 Testing Strategy

### Unit Tests

#### Backend Tests
**File**: `backend/tests/test_alerting.py`
```python
import pytest
from app.alerting import calculate_error_rate, check_alerts
from app.db.models import TraceSpan

@pytest.mark.asyncio
async def test_high_cost_alert():
    """Verify alert fires when session cost > $0.50"""
    db = AsyncSession(...)  # fixture
    
    # Create spans that total > $0.50
    span = TraceSpan(
        trace_id="123", span_id="abc",
        session_id="user-1", model="gpt-4o",
        cost_usd=0.75, latency_ms=100,
        name="test", prompt="hi", response="hello"
    )
    db.add(span)
    await db.commit()
    
    alerts = await check_alerts(db, span)
    assert len(alerts) > 0
    assert alerts[0].alert_type == "high_cost_session"

@pytest.mark.asyncio
async def test_unknown_model_cost():
    """Unknown models should have 0 cost, never break"""
    from llmobs.cost import calculate_cost
    
    cost = calculate_cost("unknown-model", tokens_in=100, tokens_out=50)
    assert cost == 0.0
```

**File**: `backend/tests/test_cost_calculator.py`
```python
from llmobs.cost import calculate_cost

def test_gpt4o_pricing():
    """Verify GPT-4o pricing calculation"""
    # 100 input tokens @ 2.50e-6 USD/token = 0.00025 USD
    # 50 output tokens @ 10.00e-6 USD/token = 0.0005 USD
    # Total = 0.00075 USD
    cost = calculate_cost("gpt-4o", tokens_in=100, tokens_out=50)
    assert abs(cost - 0.00075) < 1e-6  # Allow floating point epsilon

def test_claude_pricing():
    """Verify Anthropic pricing"""
    cost = calculate_cost("claude-3-5-sonnet", tokens_in=1000, tokens_out=500)
    expected = (1000 * 3.00e-6) + (500 * 15.00e-6)
    assert abs(cost - expected) < 1e-6

def test_prefix_matching():
    """Version variants should match base model"""
    cost1 = calculate_cost("gpt-4o", tokens_in=100, tokens_out=50)
    cost2 = calculate_cost("gpt-4o-2024-08-06", tokens_in=100, tokens_out=50)
    assert abs(cost1 - cost2) < 1e-6  # Same pricing
```

### Integration Tests

**File**: `backend/tests/test_consumer.py`
```python
import pytest
import json
import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from app.consumer import consume_forever
from app.db.models import TraceSpan
from app.db.session import async_session

@pytest.mark.asyncio
async def test_consumer_batch_ingestion():
    """Verify consumer reads batch and inserts to PostgreSQL"""
    # Setup
    r = await aioredis.from_url("redis://localhost:6389", decode_responses=False)
    
    # Produce 10 spans to Redis stream
    for i in range(10):
        event = {
            "span_id": f"span-{i:02d}",
            "trace_id": "trace-123",
            "session_id": "user-1",
            "name": f"call-{i}",
            "model": "gpt-4o",
            "tokens_in": 100,
            "tokens_out": 50,
            "latency_ms": 500,
            "cost_usd": 0.00075,
            "error": None,
            "tags": {},
        }
        await r.xadd("llmobs:traces", {"data": json.dumps(event)})
    
    # Run consumer for a moment
    consumer_task = asyncio.create_task(consume_forever(engine))
    await asyncio.sleep(2)
    consumer_task.cancel()
    
    # Verify all 10 spans in database
    async with async_session() as db:
        result = await db.execute(select(func.count(TraceSpan.id)))
        count = result.scalar_one()
        assert count == 10

@pytest.mark.asyncio
async def test_end_to_end_decorator_to_dashboard():
    """E2E: SDK @observe → Redis → Consumer → API → Dashboard fetch"""
    from llmobs import observe, trace
    from unittest.mock import MagicMock
    
    # Mock OpenAI response
    mock_response = MagicMock()
    mock_response.model = "gpt-4o"
    mock_response.usage.prompt_tokens = 100
    mock_response.usage.completion_tokens = 50
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Hello, world!"
    
    @observe(name="test-call", tags={"test": True})
    def my_llm_call():
        return mock_response
    
    # Execute
    with trace(session_id="test-session", name="test-trace"):
        result = my_llm_call()
    
    # Wait for consumer to batch-insert
    await asyncio.sleep(1.5)
    
    # Verify in database
    async with async_session() as db:
        stmt = select(TraceSpan).where(TraceSpan.name == "test-call")
        result = await db.execute(stmt)
        span = result.scalars().first()
        
        assert span is not None
        assert span.session_id == "test-session"
        assert span.model == "gpt-4o"
        assert span.tokens_in == 100
        assert span.tokens_out == 50
        assert span.cost_usd > 0
```

### Load Tests

**File**: `backend/tests/load_test.py`
```python
import asyncio
import time
import random
from locust import HttpUser, task, between

class DashboardLoadTest(HttpUser):
    """Simulated concurrent dashboard users"""
    wait_time = between(2, 5)
    
    @task(3)
    def overview(self):
        self.client.get("/api/stats/overview")
    
    @task(2)
    def cost_summary(self):
        self.client.get("/api/cost/summary")
    
    @task(2)
    def latency_percentiles(self):
        self.client.get("/api/latency/percentiles")
    
    @task(1)
    def trace_detail(self):
        trace_id = random.choice(self.available_traces)
        self.client.get(f"/api/traces/{trace_id}")

# Run: locust -f load_test.py --host=http://localhost:8000 -u 50 -r 5
```

---

## 🔍 Debugging Guide

### Backend

#### Check Consumer Status
```bash
# See if consumer is processing messages
docker compose logs backend | grep "Consumer"

# Peek at Redis stream
docker compose exec redis redis-cli -n 0 XLEN llmobs:traces
docker compose exec redis redis-cli -n 0 XRANGE llmobs:traces - + COUNT 1

# Check consumer group lag
docker compose exec redis redis-cli -n 0 XINFO GROUPS llmobs:traces
```

#### Database Queries
```bash
# Connect to PostgreSQL
docker compose exec postgres psql -U postgres -d llmobs

# Count spans by model
SELECT model, COUNT(*) FROM trace_spans GROUP BY model;

# Find expensive sessions
SELECT session_id, SUM(cost_usd) as total_cost
FROM trace_spans
WHERE session_id IS NOT NULL
GROUP BY session_id
ORDER BY total_cost DESC
LIMIT 10;

# Check latency percentiles
SELECT 
  percentile_cont(0.50) WITHIN GROUP (ORDER BY latency_ms) as p50,
  percentile_cont(0.95) WITHIN GROUP (ORDER BY latency_ms) as p95,
  percentile_cont(0.99) WITHIN GROUP (ORDER BY latency_ms) as p99
FROM trace_spans;

# Find unresolved alerts
SELECT * FROM cost_alerts WHERE resolved = false ORDER BY fired_at DESC;
```

### Frontend

#### Browser DevTools
```javascript
// In dashboard page.js, add debug logging:
async function loadData() {
  console.time('api-fetch');
  const data = await fetchOverview();
  console.timeEnd('api-fetch');
  console.log('Stats:', data);
  setStats(data);
}
```

#### Check API Responses
```bash
# Overview stats
curl -s http://localhost:8000/api/stats/overview | jq .

# Cost summary
curl -s http://localhost:8000/api/cost/summary | jq .

# Latency percentiles
curl -s http://localhost:8000/api/latency/percentiles | jq .

# List sessions
curl -s http://localhost:8000/api/traces/sessions | jq .
```

### SDK

#### Verify Decorator Works
```python
from llmobs import observe, trace
from llmobs.context import get_current_trace_id, get_current_session_id

@observe(name="test")
def my_func():
    print(f"Trace ID: {get_current_trace_id()}")
    print(f"Session ID: {get_current_session_id()}")
    return "hello"

with trace(session_id="user-123"):
    result = my_func()
    # Output should show: Trace ID: <uuid>, Session ID: user-123
```

---

## 🛠️ Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| `ImportError: No module named 'sqlalchemy'` | Backend deps not installed | `pip install -r backend/requirements.txt` |
| Dashboard blank / 404 | Backend not running | `docker compose logs backend` |
| Spans not appearing | Consumer crashed | `docker compose restart backend` |
| Database full | No retention policy | Set `DELETE FROM trace_spans WHERE created_at < NOW() - INTERVAL '7 days';` |
| Redis connection refused | Redis not started | `docker compose up redis -d` |
| API slow | Too many concurrent users | Increase PostgreSQL `pool_size` in `session.py` |
| Consumer lag high | Batch size too small | Increase `BATCH_SIZE` in `consumer.py` |

---

## 📋 Checklist: Adding a New Feature

### 1. **Database Layer** (if storing new data)
   - [ ] Add column to `TraceSpan` or new model in `models.py`
   - [ ] Create migration (or update schema in `create_all`)
   - [ ] Add index if needed

### 2. **SDK** (if capturing new data)
   - [ ] Extend `TraceEvent` schema
   - [ ] Update `@observe` decorator to capture field
   - [ ] Add unit test

### 3. **Backend** (if new API needed)
   - [ ] Add endpoint to router
   - [ ] Write SQL query (or ORM statement)
   - [ ] Add integration test

### 4. **Frontend** (if showing new data)
   - [ ] Add component
   - [ ] Fetch data via `api.js`
   - [ ] Add to page layout

### 5. **Documentation**
   - [ ] Update README if user-facing
   - [ ] Add docstring to code
   - [ ] Update this guide if procedural

---

## 📊 Performance Baselines (TODO)

Once load tests are run, fill in:

| Metric | Baseline | Target |
|--------|----------|--------|
| Span ingestion rate (spans/sec) | ? | 1000+ |
| API response time (p95) | ? | <200ms |
| Dashboard load time | ? | <2s |
| Database query time (overview) | ? | <100ms |
| Consumer lag (messages) | ? | <100 |
| Memory (backend container) | ? | <500MB |
| Memory (PostgreSQL container) | ? | <2GB (1M spans) |

---

## 🔐 Security Checklist

- [ ] Add authentication (API key or OAuth)
- [ ] Add authorization (role-based access)
- [ ] Enable HTTPS (TLS cert)
- [ ] Add rate limiting (prevent abuse)
- [ ] Implement request size limits
- [ ] Log all API access
- [ ] Sanitize user input (model names, tags)
- [ ] Add CSRF protection if session-based auth
- [ ] Regular dependency updates (`pip audit`, `npm audit`)

---

## 🚀 Deployment Checklist

- [ ] All tests passing (`pytest`, `npm test`)
- [ ] Load tests complete (throughput validated)
- [ ] Authentication implemented
- [ ] Retention policy configured
- [ ] Backups automated
- [ ] Monitoring/alerting set up
- [ ] Error budget defined
- [ ] Graceful shutdown tested
- [ ] Resource limits set
- [ ] Log aggregation configured
- [ ] Documentation complete
- [ ] Rollback plan documented

---

## 📚 Related Documentation

- [PROJECT_REVIEW.md](./PROJECT_REVIEW.md) — Full architecture analysis
- [README.md](./README.md) — User-facing quick start
- [examples/](./examples/) — Reference implementations
