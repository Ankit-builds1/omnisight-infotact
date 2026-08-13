# OmniSight Backend

FastAPI server that acts as a CI/CD webhook receiver for the OmniSight self-healing UI agent.

## Setup

```bash
python -m pip install fastapi uvicorn
```

## Run

```bash
python -m uvicorn backend.main:app --reload
```

Server runs at `http://127.0.0.1:8000`

## Endpoints

- `GET /` — health check, confirms server is running
- `POST /webhook` — receives simulated CI/CD build events (JSON body), validates input, and logs each request

## Test the webhook

Valid request:
```bash
curl.exe -X POST http://127.0.0.1:8000/webhook -H "Content-Type: application/json" -d '{\"event\": \"build_complete\", \"branch\": \"staging\"}'
```

Invalid request (tests error handling):
```bash
curl.exe -X POST http://127.0.0.1:8000/webhook -H "Content-Type: application/json" -d '{invalid json here'
```

## Status

Week 1 complete:
- Basic FastAPI app running
- `/webhook` POST endpoint built and tested
- Error handling added for invalid JSON
- Request logging added

Next (Week 2): parse VLM output into usable code fixes (Action Engine).