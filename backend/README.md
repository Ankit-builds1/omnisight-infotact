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

Week 2 complete:
- Designed VLM output JSON schema (`VLMBugReport`)
- Built the Action Engine to parse and validate VLM responses
- Added `confidence_score` and `severity_level` extraction
- Implemented malformed JSON handling (retry once, then fail gracefully)
- Built DOM cross-check layer to filter hallucinated and self-contradictory VLM output
- Documented VLM reliability findings from live integration testing
- Completed Extraction Check for Mid-Project Review

## Extraction Check — Mid-Project Review

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

Result: ✅ Cleaned and parsed successfully — Action Engine strips markdown code fences before parsing.

**5. Malformed/incomplete JSON**

Result: ✅ Retried once, then failed gracefully — logged the error and returned `None` instead of crashing the pipeline. Bug is safely skipped rather than breaking the whole run.

### Conclusion

The Action Engine successfully:
- Extracts `bug_found`, `description`, `fix`, `confidence_score`, `severity_level` from valid VLM JSON responses
- Applies our confidence-scoring feature — fixes below 0.6 confidence are automatically flagged for human review instead of blind auto-merge
- Handles malformed VLM output without crashing the pipeline

### Why This Matters

Unlike the base spec (which auto-merges AI-generated fixes with no safety check),
our Action Engine flags low-confidence fixes for mandatory human review — preventing
unreliable AI suggestions from being merged automatically. Combined with severity
classification (Critical/Major/Minor), this gives QA managers a prioritized, safety-checked
view of AI-detected bugs rather than a blind auto-fix pipeline.

## Integration Testing — VLM Reliability Findings

During live integration testing (end of Week 2), the Action Engine was run
against real VLM output for the first time. The parser worked as designed,
but the VLM output itself turned out to be unreliable in ways that
invalidated one of our safety assumptions.

### What we found

**1. Confidence scores carry no signal.**
LLaVA 1.5 7B returned `confidence_score: 1.0` while failing to detect the
deliberately injected bug (Add to Cart buttons clipped outside the viewport),
and `confidence_score: 0.9` on a clean page where it invented a bug that did
not exist. Our 0.6 threshold caught neither error — a confident miss and a
confident hallucination both pass a confidence filter.

**2. The model hallucinated UI elements.**
On `product-page.png`, the VLM reported a spelling issue in a "Comments field."
That element does not exist anywhere on the site. Prompt tightening reduced but
did not eliminate this behaviour.

**3. The model contradicted itself within a single valid response.**
One report returned `bug_found: true` with `severity_level: "Minor"`, while the
description read *"There are no visible UI bugs... The layout seems consistent"*
and the fix read *"As no UI bugs were found, no fix is required."* This is
schema-valid JSON — our Pydantic parser accepted it without complaint, and it
would have reached PR generation unchallenged.

### Root cause

`ollama show llava` reports a CLIP projector with 768 dimensions and Q4_0
quantization at 7B parameters. Screenshots at 1600×900 and above are
downscaled into that fixed input size before the model sees them, so
viewport-overflow bugs are compressed back into frame and become invisible.
We added horizontal tiling to the ML test harness to work around the
resolution limit, which improved recall but reduced precision — more tiles
meant more opportunities to hallucinate.

The team is now migrating to Qwen2.5-VL 7B, which handles native resolution
rather than forcing a fixed square input.

### Response — DOM cross-check layer

Because no VLM can be assumed reliable, the backend now verifies VLM claims
against ground truth instead of trusting the model's self-reported confidence.

`backend/app/validators/dom_check.py` applies two independent checks to every
report where `bug_found` is true:

1. **Self-consistency** — rejects reports whose description asserts that no bug
   was found, catching the contradiction case above.
2. **DOM verification** — any UI element the model quotes in its description
   must actually appear in the corresponding HTML snapshot captured by
   Playwright. Elements that do not exist in the DOM are flagged as
   hallucinations.

Failed checks set `requires_human_review` and block PR generation, with the
specific reason attached to the report.

### Test Results

| Case | Expected | Result |
|---|---|---|
| High-confidence valid bug | No review needed | ✅ |
| Low-confidence bug (0.45) | Flagged — below threshold | ✅ |
| Clean report | No review needed | ✅ |
| Markdown-fenced response | Parsed successfully | ✅ |
| Malformed JSON | Skipped safely, no crash | ✅ |
| Self-contradictory report | Blocked — contradiction detected | ✅ |
| Hallucinated element ('Comments field') | Blocked — not present in DOM | ✅ |
| Genuine bug ('Add to cart') | Verified against DOM, passed | ✅ |

Run with `python action_engine.py` from `backend/app`.

### Known limitation

The DOM check only engages when the model quotes specific element text in its
description. If it writes generic prose with no quoted element, there is
nothing to verify and the check passes by default. The ML prompt has therefore
been updated to require quoted element text whenever a bug is reported — the
validation layer and the prompt rule depend on each other.

### Why This Matters

Confidence scoring alone assumed the model knows when it is uncertain. Testing
showed it does not. The DOM cross-check replaces that assumption with
verification against the actual page, so an AI-generated fix cannot reach a
pull request unless the element it claims to fix demonstrably exists.
