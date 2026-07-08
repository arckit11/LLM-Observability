"""
LangChain integration with LLM Observability SDK.

Shows how to wrap LangChain chain steps with @observe for full visibility.

Before running:
    1. Start infrastructure: docker compose up -d postgres redis backend
    2. Install dependencies: pip install langchain langchain-openai
    3. Install the SDK: cd sdk && pip install -e .
    4. Set your OpenAI key: export OPENAI_API_KEY=sk-...

Usage:
    python examples/langchain_example.py
"""

from llmobs import observe, trace
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser


# ── Observed LangChain Calls ─────────────────────────────────────────

llm_fast = ChatOpenAI(model="gpt-4o-mini", temperature=0)
llm_quality = ChatOpenAI(model="gpt-4o", temperature=0.7)


@observe(name="langchain-classify", tags={"framework": "langchain", "step": "classify"})
def classify_topic(text: str) -> str:
    """Classify the topic of a document."""
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Classify the topic of the following text into one word: technology, science, business, health, or other."),
        ("user", "{text}"),
    ])
    chain = prompt | llm_fast | StrOutputParser()
    return chain.invoke({"text": text})


@observe(name="langchain-summarise", tags={"framework": "langchain", "step": "summarise"})
def summarise_for_topic(text: str, topic: str) -> str:
    """Summarise text with topic-specific instructions."""
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a {topic} expert. Summarise the following text in 2 sentences, highlighting key {topic} aspects."),
        ("user", "{text}"),
    ])
    chain = prompt | llm_quality | StrOutputParser()
    return chain.invoke({"text": text, "topic": topic})


@observe(name="langchain-qa-generate", tags={"framework": "langchain", "step": "qa"})
def generate_questions(summary: str, topic: str) -> str:
    """Generate discussion questions from a summary."""
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Generate 3 thought-provoking discussion questions about this {topic} summary."),
        ("user", "{summary}"),
    ])
    chain = prompt | llm_fast | StrOutputParser()
    return chain.invoke({"summary": summary, "topic": topic})


# ── Pipeline ─────────────────────────────────────────────────────────

def analyse_document(text: str, session_id: str = "langchain-demo"):
    """
    Full document analysis pipeline:
        Classify → Summarise → Generate Questions

    All steps are traced together under one trace ID.
    """
    with trace(session_id=session_id, name="document-analysis-chain"):
        print("   📂 Classifying topic...")
        topic = classify_topic(text)
        print(f"   → Topic: {topic}")

        print("   📝 Summarising...")
        summary = summarise_for_topic(text, topic)
        print(f"   → Summary: {summary[:100]}...")

        print("   ❓ Generating questions...")
        questions = generate_questions(summary, topic)
        print(f"   → Questions: {questions[:100]}...")

        return {"topic": topic, "summary": summary, "questions": questions}


if __name__ == "__main__":
    print("=" * 60)
    print("LLM Observability SDK — LangChain Integration Demo")
    print("=" * 60)

    sample = """
    Quantum computing has reached a new milestone with Google's latest
    quantum processor achieving 1,000 logical qubits with error correction.
    This breakthrough brings practical quantum computing closer to reality,
    with potential applications in drug discovery, materials science, and
    cryptography. Industry analysts predict that quantum-classical hybrid
    systems will become commercially viable within the next 3-5 years.
    """

    print("\n📄 Analysing document...")
    result = analyse_document(sample)

    print("\n" + "=" * 60)
    print("✅ Pipeline complete! All 3 LangChain calls are traced.")
    print("   Open http://localhost:3000/traces to see the full chain.")
    print("=" * 60)
