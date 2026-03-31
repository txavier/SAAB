# SAAB Knowledge AI — Local DeepSeek Setup

Run a **100% local** AI assistant trained on this SAAB knowledge base using DeepSeek via Ollama.  
No cloud, no API keys, no data leaves your machine.

## Prerequisites

| Requirement | Minimum | Link |
|---|---|---|
| **Python** | 3.10+ | https://python.org |
| **Ollama** | Latest | https://ollama.com |
| **RAM** | 8 GB (16 GB recommended) | — |
| **Disk** | ~6 GB for the 8B model | — |

## Quick Start

### One-click setup (Windows)

```powershell
.\setup.ps1
```

### Manual setup

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Make sure Ollama is running
ollama serve          # in a separate terminal if not running as a service

# 3. Pull the DeepSeek model
ollama pull deepseek-r1:8b

# 4. Ingest the SAAB docs into the vector store
python ingest.py

# 5. Start chatting
python chat.py
```

## How It Works

```
Your question
    │
    ▼
┌──────────────────┐     ┌──────────────────┐
│  Embedding Model │────▶│  ChromaDB Vector  │
│  (all-MiniLM-L6) │     │  Store (.vectordb)│
└──────────────────┘     └────────┬─────────┘
                                  │ top-5 relevant chunks
                                  ▼
                         ┌──────────────────┐
                         │  DeepSeek R1 8B  │
                         │  (Ollama local)  │
                         └────────┬─────────┘
                                  │
                                  ▼
                            AI Answer
```

1. **Ingest** (`ingest.py`): Reads all SAAB `.md` files, chunks them, embeds them with a local model, and stores vectors in ChromaDB.
2. **Chat** (`chat.py`): Your question is embedded, matched against the knowledge base, and the top matches are sent to DeepSeek as context for answering.

## Choosing a Model Size

Edit the `MODEL` variable in `chat.py`:

| Model | VRAM/RAM | Quality | Speed |
|---|---|---|---|
| `deepseek-r1:1.5b` | ~2 GB | Basic | Fast |
| `deepseek-r1:8b` | ~6 GB | Good (default) | Medium |
| `deepseek-r1:14b` | ~10 GB | Better | Slower |
| `deepseek-r1:32b` | ~20 GB | Best | Slowest |

Pull your chosen model: `ollama pull deepseek-r1:14b`

## Re-ingesting After Data Changes

If you update any `.md` files, re-run:

```bash
python ingest.py
```

This rebuilds the vector store from scratch.

## File Structure

```
SAAB/
├── 96.md            # SAAB 96 knowledge
├── C900.md          # Classic 900 knowledge
├── NG9-3.md         # New Generation 9-3 knowledge
├── NG9-5.md         # New Generation 9-5 knowledge
├── chat.py          # Interactive chatbot
├── ingest.py        # Document ingestion pipeline
├── setup.ps1        # One-click Windows setup
├── requirements.txt # Python dependencies
├── .vectordb/       # (generated) Vector store
├── Documents/       # Additional reference docs
└── k8s/             # Docker & Kubernetes files
    ├── Dockerfile       # Production container image
    ├── Dockerfile.dev   # Dev sandbox container image
    ├── k8s-deployment.yaml  # K8s standalone chat deploy
    ├── k8s-dev.yaml         # K8s dev sandbox deploy
    └── QuickStart.md        # K8s setup instructions
```
