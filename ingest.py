"""
Ingest SAAB markdown docs into a local ChromaDB vector store.
Uses sentence-transformers for embeddings — fully offline, no API keys.
"""

import os
import glob
import chromadb
from sentence_transformers import SentenceTransformer

DOCS_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(DOCS_DIR, ".vectordb")
COLLECTION = "saab_knowledge"
CHUNK_SIZE = 800  # characters per chunk
CHUNK_OVERLAP = 100


def load_markdown_files(directory: str) -> list[dict]:
    """Load all .md files (except README and Template) and return as documents."""
    docs = []
    for path in glob.glob(os.path.join(directory, "*.md")):
        basename = os.path.basename(path)
        if basename.lower() in ("readme.md", "template.md"):
            continue
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        docs.append({"source": basename, "text": text})
    return docs


def chunk_text(text: str, source: str) -> list[dict]:
    """Split text into overlapping chunks, preserving section headers."""
    chunks = []
    current_header = source  # default context is the filename
    lines = text.split("\n")
    current_chunk = []
    current_len = 0

    for line in lines:
        # Track the most recent markdown header for context
        stripped = line.strip()
        if stripped.startswith("#"):
            current_header = stripped.lstrip("#").strip()

        current_chunk.append(line)
        current_len += len(line) + 1  # +1 for newline

        if current_len >= CHUNK_SIZE:
            chunk_text_str = "\n".join(current_chunk)
            chunks.append({
                "text": chunk_text_str,
                "source": source,
                "section": current_header,
            })
            # Keep overlap by retaining the last few lines
            overlap_lines = []
            overlap_len = 0
            for prev_line in reversed(current_chunk):
                overlap_len += len(prev_line) + 1
                overlap_lines.insert(0, prev_line)
                if overlap_len >= CHUNK_OVERLAP:
                    break
            current_chunk = overlap_lines
            current_len = overlap_len

    # Don't forget the last chunk
    if current_chunk:
        chunk_text_str = "\n".join(current_chunk)
        if chunk_text_str.strip():
            chunks.append({
                "text": chunk_text_str,
                "source": source,
                "section": current_header,
            })

    return chunks


def main():
    print("Loading SAAB documents...")
    docs = load_markdown_files(DOCS_DIR)
    print(f"  Found {len(docs)} document(s): {[d['source'] for d in docs]}")

    print("Chunking documents...")
    all_chunks = []
    for doc in docs:
        chunks = chunk_text(doc["text"], doc["source"])
        all_chunks.extend(chunks)
    print(f"  Created {len(all_chunks)} chunks")

    print("Loading embedding model (first run downloads ~90MB)...")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    print("Embedding chunks...")
    texts = [c["text"] for c in all_chunks]
    embeddings = model.encode(texts, show_progress_bar=True).tolist()

    print("Storing in ChromaDB...")
    client = chromadb.PersistentClient(path=DB_DIR)
    # Delete existing collection if re-ingesting
    try:
        client.delete_collection(COLLECTION)
    except ValueError:
        pass
    collection = client.create_collection(
        name=COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )

    ids = [f"chunk_{i}" for i in range(len(all_chunks))]
    metadatas = [{"source": c["source"], "section": c["section"]} for c in all_chunks]

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas,
    )

    print(f"\nDone! {len(all_chunks)} chunks stored in {DB_DIR}")
    print("You can now run: python chat.py")


if __name__ == "__main__":
    main()
