"""
Local SAAB Knowledge chatbot — DeepSeek via Ollama + ChromaDB RAG.
Runs 100% on your machine, no internet needed after setup.

Inference backends:
  - Default (Ollama):  python chat.py
  - Fast (Ollama Q2):  FAST=1 python chat.py
  - BitNet (llama.cpp): BITNET=1 python chat.py   (run ./start_bitnet.sh first)
"""

import os
import json
import requests
import chromadb
from sentence_transformers import SentenceTransformer

DOCS_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(DOCS_DIR, ".vectordb")
COLLECTION = "saab_knowledge"
TOP_K = 5  # number of context chunks to retrieve

# ── Backend selection ──
# BITNET=1 → llama.cpp server with IQ2_XXS (~1.58 bpw) BitNet-style kernels
# FAST=1   → Ollama with aggressively quantized model (Q2_K / 1.5B)
# default  → Ollama with deepseek-r1:8b
USE_BITNET = os.environ.get("BITNET", "").strip() in ("1", "true", "yes")
USE_FAST = os.environ.get("FAST", "").strip() in ("1", "true", "yes")

if USE_BITNET:
    BACKEND_URL = os.environ.get("BITNET_URL", "http://localhost:8081")
    MODEL = "bitnet"  # placeholder, model is loaded by llama-server
    BACKEND = "bitnet"
elif USE_FAST:
    BACKEND_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
    MODEL = os.environ.get("FAST_MODEL", "deepseek-r1:1.5b")
    BACKEND = "ollama"
else:
    BACKEND_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
    MODEL = "deepseek-r1:8b"  # change to deepseek-r1:14b or deepseek-r1:32b for better quality
    BACKEND = "ollama"

SYSTEM_PROMPT = """You are a SAAB vehicle expert assistant. You help owners maintain, repair, and upgrade their SAAB cars.
You answer questions using ONLY the provided context from the SAAB knowledge base.
If the context doesn't contain enough information to answer, say so honestly.
Always mention the specific SAAB model (96, C900, NG9-3, NG9-5) when relevant.
Include links from the knowledge base when available."""


def check_backend():
    """Verify the inference backend is running and the model is available."""
    if BACKEND == "bitnet":
        # llama.cpp server health check
        try:
            r = requests.get(f"{BACKEND_URL}/health", timeout=5)
            if r.ok:
                print(f"BitNet llama.cpp server ready at {BACKEND_URL}")
                return True
            print(f"BitNet server returned {r.status_code}.")
            return False
        except requests.ConnectionError:
            print("ERROR: BitNet llama.cpp server is not running.")
            print("Start it with: ./start_bitnet.sh")
            print("(First-time setup: ./setup_bitnet.sh)")
            return False

    # Ollama backend
    try:
        r = requests.get(f"{BACKEND_URL}/api/tags", timeout=5)
        r.raise_for_status()
        models = [m["name"] for m in r.json().get("models", [])]
        if not any(MODEL in m for m in models):
            print(f"Model '{MODEL}' not found. Pulling it now (this may take a while)...")
            pull = requests.post(
                f"{BACKEND_URL}/api/pull",
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


def query_llm(prompt: str, context: str) -> str:
    """Send a prompt to the active inference backend."""
    full_prompt = f"""Context from SAAB knowledge base:
---
{context}
---

User question: {prompt}

Provide a helpful answer based on the context above."""

    if BACKEND == "bitnet":
        return _query_llamacpp(full_prompt)
    return _query_ollama(full_prompt)


def _query_llamacpp(full_prompt: str) -> str:
    """Query the llama.cpp server (OpenAI-compatible /v1/chat/completions)."""
    r = requests.post(
        f"{BACKEND_URL}/v1/chat/completions",
        json={
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": full_prompt},
            ],
            "stream": True,
            "temperature": 0.7,
            "max_tokens": 1024,
        },
        stream=True,
        timeout=300,
    )
    if not r.ok:
        print(f"\nllama.cpp error ({r.status_code}): {r.text}")
        return ""

    response_text = ""
    for line in r.iter_lines():
        if not line:
            continue
        line_str = line.decode("utf-8", errors="replace")
        if line_str.startswith("data: "):
            data_str = line_str[6:]
            if data_str.strip() == "[DONE]":
                break
            try:
                data = json.loads(data_str)
                token = data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                if token:
                    print(token, end="", flush=True)
                    response_text += token
            except json.JSONDecodeError:
                continue
    print()
    return response_text


def _query_ollama(full_prompt: str) -> str:
    """Send a prompt to the local DeepSeek model via Ollama."""

    r = requests.post(
        f"{BACKEND_URL}/api/chat",
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
    if not r.ok:
        try:
            detail = r.json().get("error", r.text)
        except Exception:
            detail = r.text
        print(f"\nOllama error ({r.status_code}): {detail}")
        return ""

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
    if not check_backend():
        return

    backend_label = {
        "bitnet": "BitNet llama.cpp (IQ2_XXS ~1.58 bpw)",
        "ollama": f"Ollama ({MODEL})",
    }[BACKEND]

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
    print(f"  SAAB Knowledge Assistant — {backend_label}")
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
        query_llm(question, context)


if __name__ == "__main__":
    main()
