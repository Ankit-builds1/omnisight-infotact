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

## Extraction Check — Mid-Project Review (Week 2, Day 5)

The Action Engine (`backend/app/action_engine.py`) parses the VLM's JSON output
and extracts the bug report fields, validated against the `VLMBugReport` schema.

### Test Results

**1. Valid bug report (high confidence)**
Input: `{"bug_found": true, "description": "Checkout button clipped on mobile", "fix": "Add overflow-x: hidden", "confidence_score": 0.85, "severity_level": "Major"}`
Result: ✅ Parsed successfully. `needs_human_review = False`

**2. Valid bug report (low confidence)**
Input: confidence_score 0.45
Result: ✅ Parsed successfully. `needs_human_review = True` — correctly flagged for manual review instead of auto-merge.

**3. Clean report (no bug)**
Result: ✅ Parsed successfully. `bug_found = False`, `needs_human_review = False`

**4. Response wrapped in markdown code fences**
Result: ✅ Cleaned and parsed successfully — Action Engine strips `json` code fences before parsing.

**5. Malformed/incomplete JSON**
Result: ✅ Retried once, then failed gracefully — logged the error and returned `None` instead of crashing the pipeline. Bug is safely skipped rather than breaking the whole run.

### Conclusion
The Action Engine successfully:
- Extracts `bug_found`, `description`, `fix`, `confidence_score`, `severity_level` from valid VLM JSON responses
- Applies our confidence-scoring feature — fixes below 0.6 confidence are automatically flagged for human review instead of blind auto-merge
- Handles malformed VLM output without crashing the pipeline