"""
Local SAAB Knowledge chatbot — DeepSeek via Ollama + ChromaDB RAG.
Runs 100% on your machine, no internet needed after setup.
"""

import os
import json
import requests
import chromadb
from sentence_transformers import SentenceTransformer

DOCS_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(DOCS_DIR, ".vectordb")
COLLECTION = "saab_knowledge"
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
MODEL = "deepseek-r1:8b"  # change to deepseek-r1:14b or deepseek-r1:32b for better quality
TOP_K = 5  # number of context chunks to retrieve

SYSTEM_PROMPT = """You are a SAAB vehicle expert assistant. You help owners maintain, repair, and upgrade their SAAB cars.
You answer questions using ONLY the provided context from the SAAB knowledge base.
If the context doesn't contain enough information to answer, say so honestly.
Always mention the specific SAAB model (96, C900, NG9-3, NG9-5) when relevant.
Include links from the knowledge base when available."""


def check_ollama():
    """Verify Ollama is running and the model is available."""
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        r.raise_for_status()
        models = [m["name"] for m in r.json().get("models", [])]
        if not any(MODEL in m for m in models):
            print(f"Model '{MODEL}' not found. Pulling it now (this may take a while)...")
            pull = requests.post(
                f"{OLLAMA_URL}/api/pull",
                json={"name": MODEL},
                stream=True,
                timeout=600,
            )
            for line in pull.iter_lines():
                if line:
                    status = json.loads(line).get("status", "")
                    if status:
                        print(f"  {status}", end="\r")
            print()
        return True
    except requests.ConnectionError:
        print("ERROR: Ollama is not running.")
        print("Install it from https://ollama.com and run: ollama serve")
        return False


def query_ollama(prompt: str, context: str) -> str:
    """Send a prompt to the local DeepSeek model via Ollama."""
    full_prompt = f"""Context from SAAB knowledge base:
---
{context}
---

User question: {prompt}

Provide a helpful answer based on the context above."""

    r = requests.post(
        f"{OLLAMA_URL}/api/chat",
        json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": full_prompt},
            ],
            "stream": True,
        },
        stream=True,
        timeout=300,
    )
    r.raise_for_status()

    response_text = ""
    for line in r.iter_lines():
        if line:
            data = json.loads(line)
            token = data.get("message", {}).get("content", "")
            print(token, end="", flush=True)
            response_text += token
            if data.get("done"):
                break
    print()  # newline after streaming
    return response_text


def main():
    if not check_ollama():
        return

    print("Loading embedding model...")
    embedder = SentenceTransformer("all-MiniLM-L6-v2")

    print("Connecting to vector store...")
    client = chromadb.PersistentClient(path=DB_DIR)
    try:
        collection = client.get_collection(COLLECTION)
    except ValueError:
        print("ERROR: Vector store not found. Run 'python ingest.py' first.")
        return

    count = collection.count()
    print(f"Loaded {count} knowledge chunks.\n")
    print("=" * 60)
    print("  SAAB Knowledge Assistant (DeepSeek local)")
    print("  Type your question, or 'quit' to exit.")
    print("=" * 60)

    while True:
        try:
            question = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not question:
            continue
        if question.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        # Retrieve relevant chunks
        q_embedding = embedder.encode([question]).tolist()
        results = collection.query(
            query_embeddings=q_embedding,
            n_results=TOP_K,
        )

        # Build context from retrieved chunks
        context_parts = []
        sources = set()
        for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
            source = meta.get("source", "unknown")
            section = meta.get("section", "")
            sources.add(source)
            context_parts.append(f"[{source} — {section}]\n{doc}")

        context = "\n\n".join(context_parts)

        print(f"\n(Sources: {', '.join(sources)})")
        print("\nAssistant: ", end="")
        query_ollama(question, context)


if __name__ == "__main__":
    main()
