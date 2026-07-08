#!/usr/bin/env python3
"""
Seed data generator for the LLM Observability Platform.

Generates realistic synthetic trace data and pushes it directly to the
Redis Stream, which the backend consumer will drain into PostgreSQL.

This populates the dashboard with impressive demo data.

Usage:
    # With Redis running (via docker compose):
    python scripts/seed_data.py

    # Custom count:
    python scripts/seed_data.py --count 5000

    # Direct DB mode (bypasses Redis, writes directly to PostgreSQL):
    python scripts/seed_data.py --direct
"""

import argparse
import json
import random
import time
import uuid
from datetime import datetime, timedelta, timezone

import redis

# ── Configuration ────────────────────────────────────────────────────

MODELS = [
    {"name": "gpt-4o",           "latency_range": (800, 4000),   "cost_in": 0.005,    "cost_out": 0.015},
    {"name": "gpt-4o-mini",      "latency_range": (200, 1200),   "cost_in": 0.000150, "cost_out": 0.000600},
    {"name": "gpt-4-turbo",      "latency_range": (1000, 5000),  "cost_in": 0.010,    "cost_out": 0.030},
    {"name": "claude-3-5-sonnet","latency_range": (600, 3500),   "cost_in": 0.003,    "cost_out": 0.015},
    {"name": "claude-3-haiku",   "latency_range": (150, 800),    "cost_in": 0.00025,  "cost_out": 0.00125},
    {"name": "gemini-1.5-flash", "latency_range": (100, 600),    "cost_in": 0.000075, "cost_out": 0.000300},
    {"name": "gemini-1.5-pro",   "latency_range": (500, 3000),   "cost_in": 0.00125,  "cost_out": 0.005},
]

SPAN_NAMES = [
    "intent-extractor", "response-generator", "document-summariser",
    "sentiment-analyser", "product-matcher", "code-reviewer",
    "email-composer", "data-extractor", "query-rewriter",
    "translation-agent", "content-moderator", "chatbot-responder",
    "report-generator", "search-ranker", "recommendation-engine",
]

SESSION_IDS = [f"user-{i}" for i in range(1, 51)]

TAGS_POOL = [
    {"team": "commerce", "env": "prod"},
    {"team": "commerce", "env": "staging"},
    {"team": "support", "env": "prod"},
    {"team": "content", "env": "prod"},
    {"team": "analytics", "env": "dev"},
    {"team": "platform", "env": "prod"},
    {"feature": "doc-upload"},
    {"feature": "search"},
    {"feature": "chat"},
    {"feature": "analytics"},
    {"agent": "router"},
    {"agent": "worker"},
]

SAMPLE_PROMPTS = [
    "Summarise the following quarterly report...",
    "Extract the key entities from this support ticket...",
    "Generate a product description for: wireless noise-cancelling headphones...",
    "Translate the following to French: ...",
    "Classify the sentiment of this customer review...",
    "Rewrite this SQL query to be more efficient...",
    "Draft a professional email response to this complaint...",
    "What are the main takeaways from this research paper?",
    "Generate 5 blog post titles about AI observability...",
    "Explain this error log in plain English...",
]

SAMPLE_RESPONSES = [
    "The quarterly report highlights a 23% revenue increase...",
    "Key entities: Customer (John Smith), Product (Widget Pro), Issue (billing)...",
    "Experience premium audio with our wireless noise-cancelling headphones...",
    "Résumé du rapport trimestriel...",
    "Sentiment: Positive. The customer expresses satisfaction with...",
    "Optimised query: SELECT ... WITH indexed_scan AS ...",
    "Dear Customer, Thank you for bringing this to our attention...",
    "The main takeaways from this paper are: 1) LLM costs...",
    "1. 'Why Every AI Team Needs Observability'\n2. ...",
    "The error indicates a connection timeout to the database...",
]

ERROR_MESSAGES = [
    None, None, None, None, None, None, None, None, None, None,  # 90% success
    "Rate limit exceeded. Please retry after 30 seconds.",
    "Connection timeout after 30000ms",
    "Invalid API key provided",
    "Model overloaded. Please try again later.",
    "Context length exceeded: 128000 tokens maximum",
]


def generate_span(trace_id: str, session_id: str, base_time: datetime) -> dict:
    """Generate a single realistic trace span."""
    model_info = random.choice(MODELS)
    model = model_info["name"]
    latency_ms = random.randint(*model_info["latency_range"])

    # Occasionally add latency spikes
    if random.random() < 0.05:
        latency_ms = int(latency_ms * random.uniform(2.0, 5.0))

    tokens_in = random.randint(50, 4000)
    tokens_out = random.randint(20, 2000)

    cost_usd = (tokens_in / 1000 * model_info["cost_in"]) + \
               (tokens_out / 1000 * model_info["cost_out"])

    error = random.choice(ERROR_MESSAGES)

    # Offset timestamp randomly within the last 7 days
    offset = timedelta(
        seconds=random.randint(0, int((datetime.now(timezone.utc) - base_time).total_seconds()))
    )
    timestamp = base_time + offset

    return {
        "span_id": str(uuid.uuid4())[:8],
        "trace_id": trace_id,
        "session_id": session_id,
        "name": random.choice(SPAN_NAMES),
        "model": model,
        "prompt": random.choice(SAMPLE_PROMPTS),
        "response": "" if error else random.choice(SAMPLE_RESPONSES),
        "tokens_in": tokens_in if not error else 0,
        "tokens_out": tokens_out if not error else 0,
        "cost_usd": round(cost_usd, 8) if not error else 0.0,
        "latency_ms": latency_ms,
        "error": error,
        "tags": random.choice(TAGS_POOL),
        "timestamp": timestamp.isoformat(),
    }


def generate_trace(base_time: datetime) -> list[dict]:
    """Generate a trace with 1-5 grouped spans."""
    trace_id = str(uuid.uuid4())
    session_id = random.choice(SESSION_IDS)
    num_spans = random.choices([1, 2, 3, 4, 5], weights=[30, 30, 25, 10, 5])[0]

    return [generate_span(trace_id, session_id, base_time) for _ in range(num_spans)]


def seed_via_redis(count: int, host: str = "localhost", port: int = 6379):
    """Push synthetic spans to Redis Stream."""
    r = redis.Redis(host=host, port=port, decode_responses=True)

    # Test connection
    try:
        r.ping()
    except redis.ConnectionError:
        print("❌ Cannot connect to Redis. Is it running?")
        print("   Start it with: docker compose up -d redis")
        return

    base_time = datetime.now(timezone.utc) - timedelta(days=7)
    total_spans = 0
    total_cost = 0.0

    print(f"🌱 Seeding {count} traces to Redis Stream...")
    start = time.time()

    for i in range(count):
        spans = generate_trace(base_time)
        for span in spans:
            r.xadd(
                "llmobs:traces",
                {"data": json.dumps(span)},
                maxlen=100_000,
            )
            total_spans += 1
            total_cost += span["cost_usd"]

        if (i + 1) % 500 == 0:
            elapsed = time.time() - start
            rate = (i + 1) / elapsed
            print(f"   📊 {i + 1}/{count} traces ({total_spans} spans) — {rate:.0f} traces/sec")

    elapsed = time.time() - start
    print(f"\n✅ Done! Seeded {total_spans} spans across {count} traces in {elapsed:.1f}s")
    print(f"   💰 Total synthetic cost: ${total_cost:.4f}")
    print(f"   📈 Stream length: {r.xlen('llmobs:traces')}")
    print(f"\n   The backend consumer will drain these into PostgreSQL.")
    print(f"   Open http://localhost:3000 to see the dashboard populate!")


def main():
    parser = argparse.ArgumentParser(description="Seed the LLM Observability Platform with synthetic data")
    parser.add_argument("--count", type=int, default=2000, help="Number of traces to generate (default: 2000)")
    parser.add_argument("--host", type=str, default="localhost", help="Redis host (default: localhost)")
    parser.add_argument("--port", type=int, default=6379, help="Redis port (default: 6379)")
    args = parser.parse_args()

    seed_via_redis(args.count, args.host, args.port)


if __name__ == "__main__":
    main()
