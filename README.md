# Federated Learning Platform For Distributed Defence Systems
### PRIVACY-PRESERVING AND SECURE INTELLIGENCE

A full-stack Federated Learning platform developed as part of a DRDO research internship project. It supports configurable synchronous and asynchronous federated-learning experiments, privacy-aware training controls, secure aggregation, and an interactive dashboard for experiment management and tracking.
---

## Architecture

```
defence-fl-platform/
├── fl_engine/          Federated Learning core (FedAvg, FedAsync, FedFA, FedProx)
├── privacy/            Differential Privacy, Secure Aggregation, Budget Tracker
├── attacks/            Byzantine attack simulations
├── defense/            Robust aggregation (Krum, Trimmed Mean, Median)
├── config/             YAML config + Pydantic loader
├── backend/            FastAPI REST + WebSocket server
│   └── app/
│       ├── api/v1/     Auth, Experiments, Training, Privacy, Metrics endpoints
│       ├── models/     SQLAlchemy ORM (PostgreSQL)
│       ├── services/   Training orchestration, Auth, Privacy
│       └── websockets/ Real-time metrics broadcast
└── frontend/           React 18 + TypeScript + Tailwind dark-theme UI
```

## Implemented FL Algorithms

| Algorithm | Type | Key Feature |
|-----------|------|-------------|
| **FedAvg** | Synchronous | Weighted averaging, McMahan et al. 2017 |
| **FedAsync** | Asynchronous | Staleness-weighted updates, virtual-clock simulation |
| **FedFA** | Async + Buffer | Deque-buffered batched weighted merge |
| **FedProx** | Synchronous | Proximal regularization for non-IID (Li et al. 2020) |

## Privacy Mechanisms

- **Differential Privacy** — Gaussian mechanism: gradient clipping + calibrated noise
- **Secure Aggregation** — Additive secret sharing masking (masks cancel on aggregation)
- **Budget Tracker** — Per-round (ε, δ) accounting with alert thresholds

---

## Quick Start (Docker)

### Prerequisites
- Docker Desktop (Windows/Mac) or Docker Engine + Compose (Linux)
- 8 GB RAM recommended (PyTorch + MNIST ~2 GB)

### 1. Clone / unzip the project
```bash
cd defence-fl-platform
```

### 2. Launch everything
```bash
docker compose up --build
```
This builds all three services (db, backend, frontend) and starts them.
First build takes 5–10 minutes (downloads PyTorch ~700 MB).

### 3. Open the platform
| Service   | URL |
|-----------|-----|
| Frontend  | http://localhost |
| API       | http://localhost:8000 |
| Swagger   | http://localhost:8000/docs |

### 4. Login
```
Create a new account using the registration page, then sign in using Email and Password.
```

---

## Running a Training Experiment

1. Navigate to **New Training** in the sidebar
2. Set a name, choose algorithm (start with **FedAvg**)
3. Dataset: **MNIST** (downloads automatically, ~12 MB)
4. Clients: 10, Rounds: 5, Local Epochs: 2
5. Click **LAUNCH EXPERIMENT**
6. Watch live accuracy and loss charts update via WebSocket

---

## Enabling Privacy Features

### Differential Privacy
- Toggle **Differential Privacy (ε,δ)** in the Privacy section of the form
- Noise Multiplier σ = 1.0, Max Gradient Norm C = 1.0
- After training, visit **Privacy Monitor** to see ε accumulation chart

### Secure Aggregation
- Toggle **Secure Aggregation (Additive Masking)**
- Masks are generated and cancelled per round (simulated locally)

---

## Development Commands

```bash
# Start platform (builds + runs)
make up

# View logs
make logs

# View backend logs only
make logs-backend

# Stop everything
make down

# Full rebuild (after code changes)
make build

# Clean volumes + containers
make clean
```

---

## API Reference

Full interactive docs at http://localhost:8000/docs

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/auth/login` | POST | Obtain JWT token |
| `/api/v1/auth/register` | POST | Create account |
| `/api/v1/experiments` | GET/POST | List / create experiments |
| `/api/v1/experiments/{id}` | GET/DELETE | Detail / delete |
| `/api/v1/training/{id}/start` | POST | Start training |
| `/api/v1/training/{id}/cancel` | POST | Cancel training |
| `/api/v1/training/{id}/status` | GET | Polling status |
| `/api/v1/training/ws/{id}` | WS | Live metrics stream |
| `/api/v1/privacy/experiments/{id}/budget` | GET | ε budget |
| `/api/v1/metrics/dashboard` | GET | Dashboard stats |

---

## Tech Stack

**Backend:** Python 3.11, FastAPI, SQLAlchemy, PostgreSQL, uvicorn, PyTorch 2.3, torchvision  
**Frontend:** React 18, TypeScript, Vite, Tailwind CSS, Recharts, React Router v6  
**Infrastructure:** Docker Compose, Nginx (reverse proxy + SPA), PostgreSQL 16  
**ML:** FedAvg, FedAsync, FedFA, FedProx, Differential Privacy (Gaussian Mechanism), Secure Aggregation (Additive Secret Sharing)

---

## Author

Kundan Patidar · IIIT Nagpur · CSE (Data Science & Analytics) · Batch 2024–28
