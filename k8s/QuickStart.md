# Quick Start — SAAB AI Dev Environment in Kubernetes

## Prerequisites

The K8s manifests pull images from a **local registry** at `192.168.87.35:5000`.
This registry runs on the control-plane node and is already configured across all
cluster nodes via the `registry-config-daemonset` (from the RobinhoodBot project).

## Building Images

After building, images must be pushed to the local registry so Kubernetes
(containerd) can pull them. Choose the method that matches your setup.

### Docker (Docker Engine installed on the build machine)

```bash
# Option A image — standalone chat
docker build -f k8s/Dockerfile -t saab-ai .
docker tag saab-ai:latest localhost:5000/saab-ai:latest
docker push localhost:5000/saab-ai:latest

# Option B image — dev sandbox
docker build -f k8s/Dockerfile.dev -t saab-dev .
docker tag saab-dev:latest localhost:5000/saab-dev:latest
docker push localhost:5000/saab-dev:latest
```

> **Note:** If building on a remote machine, use `192.168.87.35:5000` instead of
> `localhost:5000` and ensure Docker is configured to allow the insecure registry
> (`/etc/docker/daemon.json` → `"insecure-registries": ["192.168.87.35:5000"]`).

### containerd / nerdctl (no Docker)

```bash
# Option A image — standalone chat
sudo nerdctl build -f k8s/Dockerfile -t 192.168.87.35:5000/saab-ai:latest .
sudo nerdctl push --insecure-registry 192.168.87.35:5000/saab-ai:latest

# Option B image — dev sandbox
sudo nerdctl build -f k8s/Dockerfile.dev -t 192.168.87.35:5000/saab-dev:latest .
sudo nerdctl push --insecure-registry 192.168.87.35:5000/saab-dev:latest
```

---

## Option A: Standalone Chat (headless)

```powershell
# Build and push the image first (see "Building Images" above)
kubectl apply -f k8s/k8s-deployment.yaml
kubectl -n saab-ai logs -f job/pull-deepseek-model
kubectl -n saab-ai attach -it deployment/saab-chat
```

## Option B: Dev Sandbox (VS Code in K8s)

### 1. Build and deploy

```powershell
# Build and push the dev image first (see "Building Images" above)

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

**Install the Kubernetes and Dev Containers extensions** in VS Code, then:

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