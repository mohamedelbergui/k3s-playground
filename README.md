# k3s Playground

> Portfolio project dedicated to gaining hands-on, in-depth experience with Kubernetes (k3s).

An asynchronous image-processing pipeline (upload → resize/filter → storage), designed to exercise the core Kubernetes objects: **Deployment, Job, CronJob, DaemonSet, ConfigMap, Secret, PVC, Ingress, NetworkPolicy, RBAC, HPA**, plus an **Operator / Custom Resource** (CloudNativePG) for a highly available PostgreSQL.

## Architecture

```
                        ┌──────────────┐
Client ──► Ingress ───► │  Flask API   │ ──► Redis (queue) ──► Worker (Python/Pillow)
 (playground.local)     └──────┬───────┘                              │
                               │                                      │
                               └────────────► PostgreSQL ◄────────────┘
                                         (CloudNativePG, 3 instances)

        API + Worker share one PVC (originals/ and processed/ images)
```

- **API** (Flask): web UI (upload, gallery, trash) and endpoints to submit images and processing requests; exposes `/health/live` and `/health/ready` for the probes
- **Queue** (Redis): decouples the API from the worker
- **Worker** (Python + Pillow): applies filters and resizing
- **Database** (PostgreSQL): stores metadata / results; 1 primary + 2 replicas managed by the CloudNativePG operator
- **Cleaner** (CronJob): deletes old tasks and their images every day at midnight
- **Log shipping** (Fluent Bit DaemonSet): collects container logs from every node

### Available filters and operations
- Resize
- Blur
- Sepia
- Sharpen
- Grayscale

## Repository structure

```
.
├── api/                  # Flask API (app, routes, models, templates, static assets)
├── worker/               # Image-processing worker (Python + Pillow)
├── cleaning/             # Cleanup script run by the CronJob
├── docker-compose.yaml   # Local development without Kubernetes
└── manifests/            # Kubernetes desired state
```

### `manifests/`

| Path | Contents |
|---|---|
| `playground-ns.yaml` | `playground` Namespace + `default-deny-ingress` NetworkPolicy |
| `config.yaml` | ConfigMap `config` (DB/Redis hosts and ports, DB name, cleaning delay) |
| `secrets/*.example.yaml` | Secret templates (`postgres-secret`, `secret-config`) |
| `pvc.yaml` | PVC `uploads-pvc` (100Mi, RWO) shared by API, worker and cleaner |
| `postgres.yaml` | CloudNativePG `Cluster` (3 instances) + NetworkPolicy |
| `queue.yaml` | Redis Deployment + Service `queue-svc` + NetworkPolicy |
| `api.yaml` | API Deployment (probes, resource limits) + Service `api-svc` + NetworkPolicy |
| `worker.yaml` | Worker Deployment |
| `ingress.yaml` | Ingress for host `playground.local` → `api-svc` |
| `jobs/db-init-job.yaml` | **Job** running `db_init.py` to create the schema |
| `old-task-deleting.yaml` | **CronJob** (`0 0 * * *`) cleaning old tasks and images |
| `hpa/` | **HPAs** for `api` and `worker` (1–5 replicas, 70% CPU target) |
| `logging-fluent-bet/` | Fluent Bit **DaemonSet** and ConfigMap, and the **RBAC** objects (Namespace `logging`, ServiceAccount, ClusterRole, ClusterRoleBinding) |

## Network security

All ingress traffic in the `playground` namespace is denied by default; each component then opens only what it needs:

| Policy | Target pods | Allowed sources |
|---|---|---|
| `default-deny-ingress` | every pod in `playground` | none |
| `api-network-policy` | `app=api` | `kube-system` namespace (k3s Traefik ingress controller) |
| `queue-network-policy` | `app=queue` | `app=api`, `app=worker` |
| `postgres-network-policy` | `cnpg.io/cluster=postgres` | `app=api`, `app=worker`, `app=db-init`, the cluster's own instances (replication), and the `cnpg-system` namespace (operator) |

The worker receives no inbound traffic, so it has no allow rule.

## Prerequisites

- [k3s](https://k3s.io/) installed and running (single node is enough). A CNI that enforces NetworkPolicies is required; k3s ships one by default.
- `kubectl` configured to point to the cluster
- The [CloudNativePG operator](https://cloudnative-pg.io/documentation/current/installation_upgrade/) installed (it creates the `cnpg-system` namespace)
- Container images published on Docker Hub: `elbergui/playground-api`, `elbergui/playground-worker`, `elbergui/playground-cleaner` (build them from the `Dockerfile`s in `api/`, `worker/` and `cleaning/` if you use your own registry)
- metrics-server for the HPAs (bundled with k3s)
- An entry in `/etc/hosts` for the Ingress host (see [Access](#access))

## Local development (optional)

```bash
docker compose up --build
```

## Installation

All commands are run from the repository root.

### 1. Namespace and default-deny policy

```bash
kubectl apply -f manifests/playground-ns.yaml
```

### 2. ConfigMap

```bash
kubectl apply -f manifests/config.yaml
```

### 3. Secrets

Copy the templates, fill in your own credentials, then apply them:

```bash
cp manifests/secrets/postgres-secret.example.yaml manifests/secrets/postgres-secret.yaml
cp manifests/secrets/secret-config.example.yaml manifests/secrets/secret-config.yaml
# edit both files, then:
kubectl apply -f manifests/secrets/postgres-secret.yaml
kubectl apply -f manifests/secrets/secret-config.yaml
```

> ⚠️ `postgres-secret` is used by CloudNativePG to bootstrap the database: its `username` must match the owner declared in `postgres.yaml` (`admin`), and `secret-config` (`POSTGRES_USER` / `POSTGRES_PASSWORD`) must contain the same credentials.
>

### 4. Storage, database and queue

```bash
kubectl apply -f manifests/pvc.yaml
kubectl apply -f manifests/postgres.yaml
kubectl apply -f manifests/queue.yaml

# Wait for the PostgreSQL cluster before running the init job
kubectl wait --for=condition=Ready cluster/postgres -n playground --timeout=300s
```

### 5. Database initialisation

```bash
kubectl apply -f manifests/jobs/db-init-job.yaml
kubectl wait --for=condition=complete job/db-init -n playground --timeout=120s
```

### 6. Application

```bash
kubectl apply -f manifests/api.yaml
kubectl apply -f manifests/worker.yaml
kubectl apply -n playground -f manifests/ingress.yaml  
```

### 7. Autoscaling, cleanup and logging

```bash
kubectl apply -f manifests/hpa/
kubectl apply -f manifests/old-task-deleting.yaml

# rbac first: it creates the `logging` namespace used by the other two files
kubectl apply -f manifests/logging-fluent-bet/rbac-fluent.yaml
kubectl apply -f manifests/logging-fluent-bet/fluent-bit-config.yaml
kubectl apply -f manifests/logging-fluent-bet/fluent-bit-daementset.yaml
```

## Access

Add the Ingress host to `/etc/hosts`, using the IP of your k3s node:

```
<node-ip>  playground.local
```

Then open <http://playground.local>.

## Verify the deployment

```bash
kubectl get all -n playground
kubectl get cluster -n playground          # PostgreSQL: expect "Cluster in healthy state"
kubectl get pvc,ingress,hpa,networkpolicy -n playground
kubectl get cronjob,job -n playground
kubectl get daemonset -n logging
kubectl logs -n logging ds/fluent-bit      # collected logs (stdout output)
```

## Configuration

`manifests/config.yaml` (ConfigMap `config`), injected into the API, worker, init Job and cleaner:

| Key | Value | Description |
|---|---|---|
| `POSTGRES_HOST` | `postgres-rw` | Read/write Service of the PostgreSQL cluster (always points to the primary) |
| `POSTGRES_PORT` | `5432` | |
| `POSTGRES_DB` | `k3s-playground-db` | Created at bootstrap by the operator |
| `REDIS_HOST` / `REDIS_PORT` | `queue-svc` / `6379` | Redis queue |
| `CLEANING_AFTER` | `0` | Age threshold used by the cleaning CronJob |

The operator also exposes `postgres-ro` (replicas only) and `postgres-r` (any instance).

## Known limitations

- The `db-init` Job fails (and retries, up to 4 times) if it starts before the PostgreSQL cluster is ready.
- Fluent Bit currently writes the collected logs to stdout only; there is no log backend yet.

## Roadmap

- [x] Add a `HorizontalPodAutoscaler` (HPA) for the API and the worker
- [x] Add `NetworkPolicy` resources (default deny + per-component rules)
- [x] Add a `Job` to initialise the database
- [x] Add a `CronJob` to clean up old tasks
- [x] Add a `DaemonSet` for log shipping (Fluent Bit)
- [x] Set up RBAC (ServiceAccount + ClusterRole + ClusterRoleBinding)
- [x] Run PostgreSQL as a highly available cluster via an operator (3 instances)
- [ ] Add a script to apply/delete the whole stack in one command
- [ ] Ship logs to a real backend instead of stdout

## Status

🚧 Work in progress — Kubernetes part almost complete