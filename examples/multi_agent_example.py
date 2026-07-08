"""
Multi-agent pipeline with full trace grouping.

This demonstrates the trace() context manager, which groups multiple
LLM calls under one trace ID — making multi-step chains fully visible
in the trace explorer.

Before running:
    1. Start infrastructure: docker compose up -d postgres redis backend
    2. Install the SDK: cd sdk && pip install -e .
    3. Set your OpenAI key: export OPENAI_API_KEY=sk-...

Usage:
    python examples/multi_agent_example.py
"""

from llmobs import observe, trace
from openai import OpenAI

client = OpenAI()


# ── Agent 1: Intent Extractor ────────────────────────────────────────

@observe(name="intent-extractor", tags={"agent": "intent", "team": "commerce"})
def extract_intent(message: str):
    """Extract structured intent from user message."""
    return client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "Extract the user's intent as JSON with fields: "
                    "'action' (search/buy/compare/ask), "
                    "'category' (string), "
                    "'constraints' (dict of filters like price_max, brand, etc.)"
                ),
            },
            {"role": "user", "content": message},
        ],
    )


# ── Agent 2: Product Matcher ─────────────────────────────────────────

@observe(name="product-matcher", tags={"agent": "matcher", "team": "commerce"})
def match_products(intent_json: str):
    """Find matching products based on extracted intent."""
    return client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "Given a user intent, return a JSON list of 3 matching products. "
                    "Each product has: name, price, rating, description. "
                    "Make up realistic products."
                ),
            },
            {"role": "user", "content": f"Find products for this intent: {intent_json}"},
        ],
    )


# ── Agent 3: Response Generator ──────────────────────────────────────

@observe(name="response-generator", tags={"agent": "responder", "team": "commerce"})
def generate_response(intent_json: str, products_json: str):
    """Generate a friendly, conversational response with product recommendations."""
    return client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a helpful shopping assistant. Generate a warm, "
                    "conversational response recommending products to the user. "
                    "Include prices and brief descriptions. Be concise."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"User intent: {intent_json}\n\n"
                    f"Matching products: {products_json}\n\n"
                    "Generate a helpful response."
                ),
            },
        ],
    )


# ── Pipeline Execution ───────────────────────────────────────────────

def run_commerce_pipeline(user_message: str, session_id: str):
    """
    Run the full commerce pipeline:
        Intent → Products → Response

    All three LLM calls are grouped under one trace,
    so they appear together in the trace explorer.
    """
    with trace(session_id=session_id, name="commerce-pipeline"):
        # Step 1: Extract intent
        intent_response = extract_intent(user_message)
        intent_text = intent_response.choices[0].message.content
        print(f"   🔍 Intent: {intent_text[:100]}...")

        # Step 2: Match products
        products_response = match_products(intent_text)
        products_text = products_response.choices[0].message.content
        print(f"   📦 Products: {products_text[:100]}...")

        # Step 3: Generate response
        final_response = generate_response(intent_text, products_text)
        response_text = final_response.choices[0].message.content
        print(f"   💬 Response: {response_text[:150]}...")

        return response_text


if __name__ == "__main__":
    print("=" * 60)
    print("LLM Observability SDK — Multi-Agent Pipeline Demo")
    print("=" * 60)

    queries = [
        ("I need running shoes under 3000 rupees", "user-42"),
        ("Compare wireless earbuds for working out", "user-73"),
        ("Looking for a birthday gift for a 10-year-old who likes science", "user-108"),
    ]

    for query, sid in queries:
        print(f"\n🛒 User [{sid}]: \"{query}\"")
        run_commerce_pipeline(query, session_id=sid)

    print("\n" + "=" * 60)
    print("✅ All traces captured! Open http://localhost:3000/traces")
    print("   Each pipeline shows 3 grouped spans under one trace ID.")
    print("=" * 60)
