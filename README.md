# k3s Playground

> Portfolio project dedicated to gaining hands-on, in-depth experience with Kubernetes (k3s).

An asynchronous image-processing pipeline (upload → resize/filter → storage), designed to exercise the full range of core Kubernetes objects: **Deployment, StatefulSet, Job, CronJob, DaemonSet, ConfigMap, Secret, PVC, Ingress, NetworkPolicy, RBAC, HPA**.

## Architecture

```
Client → Flask API → Redis (queue) → Worker (Python/Pillow) → PostgreSQL
```

- **API** (Flask): receives images and processing requests
- **Queue** (Redis): decouples the API from the worker
- **Worker** (Python + Pillow): applies filters and resizing
- **Database** (PostgreSQL): stores metadata / results

### Available filters and operations
- Resize
- Blur
- Sepia
- Sharpen

## Repository structure

The `manifests/` folder contains the YAML files representing the *desired state* of each Kubernetes object:

| File | Role |
|---|---|
| `api-deployment.yaml` | Flask API deployment |
| `api-svc.yaml` | Service exposing the API |
| `worker-deployment.yaml` | Image-processing worker deployment |
| `queue-deployment.yaml` | Redis deployment |
| `queue-svc.yaml` | Service for Redis |
| `postgres-pod.yaml` | PostgreSQL pod |
| `postgres-svc.yaml` | Service for PostgreSQL |
| `postgres-pvc.yaml` | Persistent volume for PostgreSQL |
| `pvc.yaml` | Shared persistent volume (image storage) |
| `ingress.yaml` | External exposure rules |

## Prerequisites

- [k3s](https://k3s.io/) installed and running
- `kubectl` configured to point to the cluster

## Installation

### 1. Create the namespace

```bash
kubectl create ns playground
```

### 2. Create the ConfigMap

```bash
kubectl create configmap config \
  -n playground \
  --from-literal=POSTGRES_HOST=postgres-svc \
  --from-literal=POSTGRES_PORT=5432 \
  --from-literal=POSTGRES_DB=k3s-playground-db \
  --from-literal=REDIS_HOST=queue-svc \
  --from-literal=REDIS_PORT=6379
```

### 3. Create the Secret

```bash
kubectl create secret generic secret-config \
  -n playground \
  --from-literal=POSTGRES_USER=<your_username> \
  --from-literal=POSTGRES_PASSWORD=<your_password>
```

> ⚠️ Replace `<your_username>` and `<your_password>` with your own credentials.

### 4. Deploy the Kubernetes objects

```bash
cd manifests/
kubectl apply -f .
```

Or file by file if you want to control the creation order:

```bash
kubectl apply -f postgres-pvc.yaml
kubectl apply -f postgres-pod.yaml
kubectl apply -f postgres-svc.yaml
kubectl apply -f pvc.yaml
kubectl apply -f queue-deployment.yaml
kubectl apply -f queue-svc.yaml
kubectl apply -f api-deployment.yaml
kubectl apply -f api-svc.yaml
kubectl apply -f worker-deployment.yaml
kubectl apply -f ingress.yaml
```

### 5. Verify the deployment

```bash
kubectl get all -n playground
kubectl get pvc -n playground
kubectl get ingress -n playground
```

## Known limitations

- k3s's default `local-path-provisioner` only supports **ReadWriteOnce (RWO)** access mode, which limits volume sharing across multiple pods at the same time.

## Roadmap

- [ ] Add a `HorizontalPodAutoscaler` (HPA) for the worker
- [ ] Add `NetworkPolicy` resources to restrict traffic between components
- [ ] Add a `CronJob` to clean up processed images
- [ ] Add a `DaemonSet` for monitoring/log-shipping
- [ ] Set up RBAC (ServiceAccount + Role + RoleBinding)

## Status

🚧 Work in progress
