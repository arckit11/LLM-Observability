#!/usr/bin/env python3
"""
Live Demo — LLM Observability Platform

Run this and watch your dashboard at http://localhost:3000 fill up
with real-time traces, costs, and alerts.

Every few seconds a random agent fires a random LLM call.
Errors, slow calls, and cost spikes happen organically.

Usage:
    python3 examples/demo.py              # default: ~2s between calls
    python3 examples/demo.py --fast       # ~0.5s between calls
    python3 examples/demo.py --slow       # ~5s between calls

Press Ctrl+C to stop.
"""

import json
import os
import random
import sys
import time
from datetime import datetime

from llmobs import observe, trace

# ── Configuration ────────────────────────────────────────────────────

MODELS = [
    ("gpt-4o", 5.00, 15.00),           # model, input_price/1M, output_price/1M
    ("gpt-4o-mini", 0.15, 0.60),
    ("gpt-4-turbo", 10.00, 30.00),
    ("claude-3-5-sonnet", 3.00, 15.00),
    ("claude-3-haiku", 0.25, 1.25),
    ("gemini-1.5-pro", 3.50, 10.50),
    ("gemini-1.5-flash", 0.075, 0.30),
    ("gemini-2.0-flash", 0.10, 0.40),
]

SESSIONS = [
    "user-42", "user-73", "user-108", "user-201", "user-315",
    "bot-alpha", "bot-beta", "pipeline-prod", "pipeline-staging",
    "demo-session", "test-runner", "ci-agent",
]

AGENTS = [
    {
        "name": "intent-extractor",
        "tags": {"agent": "intent", "team": "commerce"},
        "prompts": [
            "Extract intent from: 'I want cheap running shoes'",
            "Extract intent from: 'Compare the best laptops under 80k'",
            "Extract intent from: 'Find me a birthday gift for a 5 year old'",
            "Extract intent from: 'What's the cheapest flight to Dubai?'",
            "Extract intent from: 'I need a waterproof backpack for hiking'",
        ],
        "responses": [
            '{"action":"search","category":"shoes","price_max":3000}',
            '{"action":"compare","category":"laptops","budget":80000}',
            '{"action":"gift","category":"toys","age":5}',
            '{"action":"search","category":"flights","destination":"Dubai"}',
            '{"action":"search","category":"backpacks","features":["waterproof"]}',
        ],
        "tokens_in": (60, 200),
        "tokens_out": (20, 60),
    },
    {
        "name": "product-matcher",
        "tags": {"agent": "matcher", "team": "commerce"},
        "prompts": [
            "Find products for intent: search/shoes",
            "Match products for intent: compare/laptops",
            "Find gift ideas for intent: gift/toys",
        ],
        "responses": [
            '[{"name":"Nike Pegasus","price":2800},{"name":"Adidas Duramo","price":2400}]',
            '[{"name":"MacBook Air M3","price":75000},{"name":"ThinkPad X1","price":72000}]',
            '[{"name":"LEGO Robotics Kit","price":3500},{"name":"Art Set","price":1200}]',
        ],
        "tokens_in": (100, 350),
        "tokens_out": (40, 120),
    },
    {
        "name": "response-generator",
        "tags": {"agent": "responder", "team": "commerce"},
        "prompts": [
            "Generate shopping response with product recommendations",
            "Create a comparison summary for the user",
            "Write a friendly gift suggestion response",
        ],
        "responses": [
            "Here are the top picks:\n1. Nike Pegasus (₹2,800)\n2. Adidas Duramo (₹2,400)",
            "Both laptops are excellent. The MacBook Air M3 offers better battery life.",
            "Great gifts for a 5-year-old: LEGO Robotics Kit sparks creativity!",
        ],
        "tokens_in": (200, 600),
        "tokens_out": (80, 200),
    },
    {
        "name": "sentiment-analyser",
        "tags": {"agent": "sentiment", "team": "analytics"},
        "prompts": [
            "Analyse sentiment: 'This product is amazing!'",
            "Analyse sentiment: 'Terrible customer service, never buying again'",
            "Analyse sentiment: 'It's okay, nothing special'",
            "Analyse sentiment: 'Best purchase I ever made'",
        ],
        "responses": ["Positive", "Negative", "Neutral", "Very Positive"],
        "tokens_in": (15, 60),
        "tokens_out": (2, 10),
    },
    {
        "name": "summariser",
        "tags": {"agent": "summariser", "team": "content"},
        "prompts": [
            "Summarise this 5000-word article about AI trends",
            "Summarise meeting transcript from engineering standup",
            "Create executive summary of quarterly report",
        ],
        "responses": [
            "Summary: AI adoption is accelerating across industries with focus on cost reduction.",
            "Key points: Sprint velocity up 15%, 2 blockers resolved, new hire onboarded.",
            "Q3 highlights: Revenue up 22% YoY, customer retention at 94%.",
        ],
        "tokens_in": (500, 3000),
        "tokens_out": (80, 400),
    },
    {
        "name": "code-reviewer",
        "tags": {"agent": "code-review", "team": "engineering"},
        "prompts": [
            "Review: def get_user(id): return db.query(f'SELECT * FROM users WHERE id={id}')",
            "Review: async function fetchData() { const res = await fetch(url); return res; }",
            "Review: for i in range(len(items)): process(items[i])",
        ],
        "responses": [
            "Found SQL injection vulnerability on line 1. Use parameterised queries.",
            "Missing error handling — add try/catch and check res.ok before returning.",
            "Use enumerate() instead of range(len()). More Pythonic and readable.",
        ],
        "tokens_in": (200, 800),
        "tokens_out": (60, 250),
    },
    {
        "name": "embedder",
        "tags": {"agent": "embedder", "team": "search"},
        "prompts": [
            "Generate embedding for document chunk #1",
            "Embed user query for vector search",
            "Create embedding for product description",
        ],
        "responses": [
            "[0.023, -0.041, 0.089, -0.012, ...]",
            "[0.067, 0.033, -0.055, 0.091, ...]",
            "[-0.018, 0.072, 0.044, -0.063, ...]",
        ],
        "tokens_in": (50, 500),
        "tokens_out": (5, 30),
    },
    {
        "name": "translator",
        "tags": {"agent": "translator", "team": "i18n"},
        "prompts": [
            "Translate to Hindi: 'Your order has been shipped'",
            "Translate to Spanish: 'Welcome to our platform'",
            "Translate to Japanese: 'Thank you for your purchase'",
        ],
        "responses": [
            "आपका ऑर्डर भेज दिया गया है",
            "Bienvenido a nuestra plataforma",
            "ご購入ありがとうございます",
        ],
        "tokens_in": (20, 100),
        "tokens_out": (15, 80),
    },
]

PIPELINE_NAMES = [
    "commerce-pipeline", "analytics-pipeline", "content-pipeline",
    "code-review-flow", "search-indexing", "translation-batch",
    "onboarding-flow", "moderation-check", "recommendation-engine",
]

# ── Mock response object ─────────────────────────────────────────────

class _Usage:
    def __init__(self, p, c):
        self.prompt_tokens = p
        self.completion_tokens = c

class _Msg:
    def __init__(self, c):
        self.content = c

class _Choice:
    def __init__(self, c):
        self.message = _Msg(c)

class MockResp:
    def __init__(self, model, content, p_tok, c_tok):
        self.model = model
        self.choices = [_Choice(content)]
        self.usage = _Usage(p_tok, c_tok)


# ── Observed functions ────────────────────────────────────────────────

def make_call(agent_cfg, model_name):
    """Build and execute a single observed LLM call."""
    prompt = random.choice(agent_cfg["prompts"])
    response = random.choice(agent_cfg["responses"])
    tok_in = random.randint(*agent_cfg["tokens_in"])
    tok_out = random.randint(*agent_cfg["tokens_out"])

    @observe(name=agent_cfg["name"], tags=agent_cfg["tags"])
    def _call(**kwargs):
        # Simulate latency
        base_latency = random.uniform(0.1, 0.8)
        time.sleep(base_latency)
        return MockResp(model_name, response, tok_in, tok_out)

    return _call(messages=[{"role": "user", "content": prompt}]), prompt, response


def make_error_call():
    """Simulate a failing LLM call."""
    errors = [
        "RateLimitError: Rate limit exceeded, retry after 30s",
        "APIConnectionError: Connection to provider timed out",
        "InvalidRequestError: Maximum context length exceeded (128k tokens)",
        "AuthenticationError: Invalid API key provided",
        "ServiceUnavailableError: The model is currently overloaded",
    ]

    @observe(name="failing-call", tags={"agent": "various", "team": "ops"})
    def _fail(**kwargs):
        time.sleep(random.uniform(0.05, 0.2))
        raise RuntimeError(random.choice(errors))

    return _fail


def make_slow_call(agent_cfg, model_name):
    """Simulate an unusually slow LLM call (>5s)."""
    prompt = random.choice(agent_cfg["prompts"])
    response = random.choice(agent_cfg["responses"])
    tok_in = random.randint(*agent_cfg["tokens_in"])
    tok_out = random.randint(*agent_cfg["tokens_out"])

    @observe(name=agent_cfg["name"] + "-slow", tags={**agent_cfg["tags"], "slow": "true"})
    def _slow(**kwargs):
        time.sleep(random.uniform(5.0, 7.0))
        return MockResp(model_name, response, tok_in, tok_out)

    return _slow(messages=[{"role": "user", "content": prompt}]), prompt


# ── Main loop ─────────────────────────────────────────────────────────

ICONS = {
    "intent-extractor": "🔍",
    "product-matcher": "📦",
    "response-generator": "💬",
    "sentiment-analyser": "🎭",
    "summariser": "📝",
    "code-reviewer": "🔎",
    "embedder": "🧮",
    "translator": "🌐",
}


def run_one():
    """Execute one random trace with 1-3 spans."""
    session = random.choice(SESSIONS)
    pipeline = random.choice(PIPELINE_NAMES)
    num_steps = random.choices([1, 2, 3], weights=[30, 45, 25])[0]

    # Decide scenario: 85% normal, 8% error, 7% slow
    roll = random.random()

    with trace(session_id=session, name=pipeline):
        if roll < 0.08:
            # ── Error scenario ──
            fn = make_error_call()
            try:
                fn(messages=[{"role": "user", "content": "trigger error"}])
            except Exception as e:
                print(f"  ❌ Error: {e}")
            return "error", session, pipeline

        if roll < 0.15:
            # ── Slow scenario ──
            agent = random.choice(AGENTS)
            model = random.choice(MODELS)[0]
            print(f"  🐢 Slow call: {agent['name']} via {model} (5-7s)...")
            make_slow_call(agent, model)
            return "slow", session, pipeline

        # ── Normal multi-step pipeline ──
        for step in range(num_steps):
            agent = random.choice(AGENTS)
            model = random.choice(MODELS)[0]
            icon = ICONS.get(agent["name"], "⚙️")
            result, prompt, response = make_call(agent, model)
            resp_preview = response[:60].replace("\n", " ")
            print(f"  {icon} {agent['name']:20s} → {model:20s} │ {resp_preview}...")

    return "ok", session, pipeline


def main():
    # Parse speed flag
    delay = 2.0
    if "--fast" in sys.argv:
        delay = 0.5
    elif "--slow" in sys.argv:
        delay = 5.0

    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║       LLM Observability Platform — Live Demo               ║")
    print("╠══════════════════════════════════════════════════════════════╣")
    print(f"║  Redis   : {os.getenv('LLMOBS_REDIS_HOST', 'localhost')}:{os.getenv('LLMOBS_REDIS_PORT', '6379'):6s}                              ║")
    print(f"║  Speed   : ~{delay}s between calls                            ║")
    print("║  Dashboard: http://localhost:3000                           ║")
    print("║                                                            ║")
    print("║  Press Ctrl+C to stop                                      ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()

    call_count = 0
    error_count = 0
    slow_count = 0
    start = time.time()

    try:
        while True:
            call_count += 1
            ts = datetime.now().strftime("%H:%M:%S")
            session = random.choice(SESSIONS)

            print(f"[{ts}] ── Trace #{call_count} ──")
            result_type, session, pipeline = run_one()

            if result_type == "error":
                error_count += 1
            elif result_type == "slow":
                slow_count += 1

            elapsed = time.time() - start
            rate = call_count / elapsed if elapsed > 0 else 0
            print(f"         ↳ session={session}  pipeline={pipeline}")
            print(f"         ↳ total={call_count}  errors={error_count}  slow={slow_count}  rate={rate:.1f}/s")
            print()

            # Add jitter to the delay
            time.sleep(delay + random.uniform(-delay * 0.3, delay * 0.3))

    except KeyboardInterrupt:
        elapsed = time.time() - start
        print(f"\n\n{'─' * 60}")
        print(f"  Demo stopped after {elapsed:.0f}s")
        print(f"  Total traces: {call_count}  |  Errors: {error_count}  |  Slow: {slow_count}")
        print(f"  Dashboard: http://localhost:3000")
        print(f"{'─' * 60}\n")


if __name__ == "__main__":
    main()
