"""
Basic LLM Observability SDK usage.

Before running:
    1. Start infrastructure: docker compose up -d postgres redis backend
    2. Install the SDK: cd sdk && pip install -e .
    3. Set your OpenAI key: export OPENAI_API_KEY=sk-...

Usage:
    python examples/basic_usage.py
"""

from llmobs import observe
from openai import OpenAI

client = OpenAI()


@observe(name="document-summariser", tags={"feature": "doc-upload", "env": "dev"})
def summarise(text: str):
    """Summarise a document using GPT-4o-mini."""
    return client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a concise summariser. Respond in 2-3 sentences."},
            {"role": "user", "content": f"Summarise this:\n\n{text}"},
        ],
    )


@observe(name="sentiment-analyser", tags={"feature": "analytics"})
def analyse_sentiment(text: str):
    """Analyse the sentiment of a piece of text."""
    return client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Classify sentiment as positive, negative, or neutral. Respond with just the label."},
            {"role": "user", "content": text},
        ],
    )


if __name__ == "__main__":
    sample_text = """
    Artificial intelligence has transformed how businesses operate. Companies are
    leveraging large language models for customer support, content generation, and
    data analysis. However, without proper observability, teams often struggle to
    track costs, debug failures, and optimise performance across their LLM pipelines.
    """

    print("=" * 60)
    print("LLM Observability SDK — Basic Usage Demo")
    print("=" * 60)

    print("\n📝 Summarising document...")
    summary_response = summarise(sample_text)
    print(f"   Summary: {summary_response.choices[0].message.content}")

    print("\n🎯 Analysing sentiment...")
    sentiment_response = analyse_sentiment(sample_text)
    print(f"   Sentiment: {sentiment_response.choices[0].message.content}")

    print("\n✅ Both calls are now captured in the dashboard!")
    print("   Open http://localhost:3000 to view traces, costs, and latency.")
