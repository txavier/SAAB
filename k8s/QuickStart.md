# Quick Start — SAAB AI Dev Environment in Kubernetes

## Option A: Standalone Chat (headless)

```powershell
# Run from repo root
docker build -f k8s/Dockerfile -t saab-ai .
kubectl apply -f k8s/k8s-deployment.yaml
kubectl -n saab-ai logs -f job/pull-deepseek-model
kubectl -n saab-ai attach -it deployment/saab-chat
```

## Option B: Dev Sandbox (VS Code in K8s)

### 1. Build and deploy

```powershell
# Run from repo root
# Build the dev image
docker build -f k8s/Dockerfile.dev -t saab-dev .

# Deploy Ollama + dev pod
kubectl apply -f k8s/k8s-dev.yaml

# Wait for the model to download (first time only)
kubectl -n saab-ai logs -f job/pull-deepseek-model
```

### 2. Clone the repo inside the pod

```powershell
kubectl -n saab-ai exec -it deployment/saab-dev -- bash
# Inside the pod:
git clone <your-repo-url> /workspace/SAAB
cd /workspace/SAAB
python ingest.py
python chat.py
```

### 3. Connect VS Code

**Install the Kubernetes extension** in VS Code, then:

1. Open the Command Palette (`Ctrl+Shift+P`)
2. Run **Kubernetes: Attach Visual Studio Code**
3. Select namespace `saab-ai` → pod `saab-dev-*`
4. VS Code reopens connected to the container
5. Open folder `/workspace/SAAB`

Alternatively, use the **Remote - Tunnels** or **Remote - SSH** approach:

```powershell
# Port-forward if you prefer Remote-SSH
kubectl -n saab-ai port-forward deployment/saab-dev 2222:22
```

### Notes

- The `/workspace` directory is on a PersistentVolumeClaim — your cloned repo
  survives pod restarts.
- The Ollama service is reachable from inside the dev pod at `http://ollama:11434`.
- Python deps and the embedding model are pre-installed in the image.
- After cloning, just run `python ingest.py` then `python chat.py`.