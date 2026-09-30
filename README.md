# Smart Guided Troubleshooting Engine (SGTE)

Samsung PRISM Theme 2 — Smart Guided Troubleshooting Engine.

## Offline demo (Phase 15)

See [`docs/offline_demo.md`](docs/offline_demo.md) for MOCK-mode startup, demo scenarios, and limitations.
The implementation gate remains unsatisfied; the demo does not imply production readiness.

## Backend (frozen)

```bash
pip install -r requirements.txt
uvicorn sgte.api:app --reload --host 127.0.0.1 --port 8000
```

- `GET /health`
- `POST /v1/troubleshoot`

See `docs/API.md` for the contract.

## Frontend

Polished React demonstration UI in `frontend/`.

```bash
cd frontend
npm install
npm run dev
```

Open http://127.0.0.1:5173 (proxies API to port 8000).

Full UI instructions: [`frontend/README.md`](frontend/README.md).

## Tests

```bash
pytest -q
python evaluation/phase7_accuracy.py
python evaluation/phase71_retrieval.py
```
