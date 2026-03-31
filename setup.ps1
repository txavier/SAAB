# ============================================
#   SAAB Knowledge Base - Local Setup
# ============================================

Write-Host ""
Write-Host "============================================"
Write-Host "  SAAB Knowledge Base - Local Setup"
Write-Host "============================================"
Write-Host ""

# Check for Python
try {
    $null = Get-Command python -ErrorAction Stop
} catch {
    Write-Host "ERROR: Python not found. Install from https://python.org" -ForegroundColor Red
    exit 1
}

# Check for Ollama
try {
    $null = Get-Command ollama -ErrorAction Stop
} catch {
    Write-Host "ERROR: Ollama not found. Install from https://ollama.com" -ForegroundColor Red
    exit 1
}

# Install Python deps
Write-Host "[1/3] Installing Python packages..."
pip install -r "$PSScriptRoot\requirements.txt" -q

# Pull DeepSeek model
Write-Host "[2/3] Pulling DeepSeek model (this may take a while on first run)..."
ollama pull deepseek-r1:8b

# Ingest docs
Write-Host "[3/3] Ingesting SAAB documents into vector store..."
python "$PSScriptRoot\ingest.py"

Write-Host ""
Write-Host "============================================"
Write-Host "  Setup complete! Run: python chat.py"
Write-Host "============================================"
