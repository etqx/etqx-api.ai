# etqx-api

A lightweight FastAPI service that exposes a strategy analysis endpoint and a simple heartbeat for health checks.

## Requirements
- Python 3.10+
- An OpenAI API key (only required for `/strategy/run`)

## Quickstart

1) Create and activate a virtual environment
- macOS/Linux:
  - `python3 -m venv .venv`
  - `source .venv/bin/activate`
- Windows (PowerShell):
  - `py -3 -m venv .venv`
  - `.venv\\Scripts\\Activate.ps1`

2) Upgrade pip and install dependencies
- `python -m pip install --upgrade pip`
- `pip install -r requirements.txt`

3) Set environment variable (required for `/strategy/run`)
- macOS/Linux: `export OPENAI_API_KEY=sk-...`
- Windows (PowerShell): `$Env:OPENAI_API_KEY = "sk-..."`

4) Run the server
- Option A (simple): `python app.py`
- Option B (uvicorn): `uvicorn app:app --reload --port 8000`

5) Test endpoints
- Health check:
  - `curl http://127.0.0.1:8000/health`
  - Response: `{ "status": "ok" }`
- Strategy run (POST):
  - `curl -X POST http://127.0.0.1:8000/strategy/run \\
      -H 'Content-Type: application/json' \\
      -d '{"strategy":"cooperative_alignment","useCase":"demo","context":"Example context."}'`

## Project Structure
- `app.py`: FastAPI application containing endpoints and core logic.
- `requirements.txt`: Python dependencies to run the service.
- `README.md`: Setup and usage instructions.

## Development Notes
- The `/health` endpoint does not require any credentials and is safe for health checks.
- The `/strategy/run` endpoint requires `OPENAI_API_KEY` and performs an external API call using `httpx`.
- To add packages, update `requirements.txt` and run `pip install -r requirements.txt` again.

## Makefile Workflow (optional, convenient)
- Create venv and install deps: `make install`
- Run the server (auto-reload): `make run`
- One-shot setup and run: `make dev`
- Clean environment and caches: `make clean`

## Common Commands
- Format: choose your preferred formatter (e.g., `ruff`, `black`) and add to `requirements.txt` if desired.
- Run with auto-reload: `uvicorn app:app --reload`
- Change port: `uvicorn app:app --reload --port 9000`

## Troubleshooting
- If `ModuleNotFoundError` occurs, confirm your virtual environment is active and dependencies are installed.
- If `/strategy/run` fails with a 500 or 502, ensure `OPENAI_API_KEY` is set and valid.
