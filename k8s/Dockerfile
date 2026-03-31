FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY *.md ./
COPY *.py ./
COPY Documents/ Documents/

# Pre-download the embedding model at build time
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Ingest docs at build time so the vector store is baked in
RUN python ingest.py

EXPOSE 8000

CMD ["python", "chat.py"]
