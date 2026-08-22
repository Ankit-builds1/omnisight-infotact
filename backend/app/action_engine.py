"""
Action Engine — OmniSight Backend

Parses the VLM's JSON response and extracts the bug report fields,
validating against the VLMBugReport schema (see schemas/vlm_output.py).

Week 2, Day 2: basic parsing of bug_found, description, fix.
Week 2, Day 3: added confidence_score + severity_level extraction, plus
    validation rules (e.g. bug_found=True must have a description and fix).
Week 2, Day 4: added malformed JSON handling — retries once, then logs and
    skips gracefully instead of crashing the whole pipeline.
Week 2 (integration testing): added DOM cross-check (see validators/dom_check.py)
    — filters out self-contradictory and hallucinated VLM reports before
    PR generation.
"""

import json
import logging
from schemas.vlm_output import VLMBugReport
from validators.dom_check import validate_report

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("action_engine")


def parse_vlm_response(raw_response: str, retry_count: int = 0) -> VLMBugReport | None:
    """
    Takes the raw JSON string returned by the VLM and parses it into
    a validated VLMBugReport object.

    If the response is malformed:
    - retries parsing once (in case of a transient formatting issue)
    - if still malformed, logs the raw response and returns None
      instead of crashing, so the pipeline can skip this bug and continue.
    """
    cleaned = _clean_response(raw_response)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        if retry_count < 1:
            logger.warning(f"JSON decode failed, retrying once. Error: {e}")
            return parse_vlm_response(raw_response, retry_count=retry_count + 1)
        else:
            logger.error(f"VLM response is not valid JSON after retry. Raw response: {raw_response}")
            return None

    try:
        report = VLMBugReport(**data)
    except Exception as e:
        if retry_count < 1:
            logger.warning(f"Schema validation failed, retrying once. Error: {e}")
            return parse_vlm_response(raw_response, retry_count=retry_count + 1)
        else:
            logger.error(f"VLM response does not match schema after retry. Raw response: {raw_response}")
            return None

    try:
        _validate_business_rules(report)
    except ValueError as e:
        logger.error(f"Business rule validation failed: {e}. Raw response: {raw_response}")
        return None

    return report


def _clean_response(raw_response: str) -> str:
    """Strip common formatting issues like markdown code fences."""
    cleaned = raw_response.strip()
    cleaned = cleaned.replace("```json", "").replace("```", "")
    return cleaned.strip()


def _validate_business_rules(report: VLMBugReport) -> None:
    """
    Extra validation beyond basic schema types:
    - if a bug is found, description/fix/severity should not be missing
    """
    if report.bug_found:
        if not report.description:
            raise ValueError("bug_found is True but description is missing")
        if not report.fix:
            raise ValueError("bug_found is True but fix is missing")
        if not report.severity_level:
            raise ValueError("bug_found is True but severity_level is missing")


def needs_human_review(
    report: VLMBugReport,
    threshold: float = 0.6,
    html_snapshot: str = None,
) -> tuple[bool, list[str]]:
    """
    Returns (needs_review, reasons).

    Do wajah se review flag hota hai:
      1. Confidence threshold se neeche
      2. DOM cross-check fail — self-contradictory report ya
         hallucinated element (see validators/dom_check.py)

    html_snapshot None ho to DOM check skip ho jaata hai, par
    self-consistency check phir bhi chalta hai.
    """
    reasons = []

    if report.bug_found and report.confidence_score < threshold:
        reasons.append(
            f"Low confidence: {report.confidence_score} < {threshold}"
        )

    is_trustworthy, check_reasons = validate_report(
        report.model_dump(),
        html_snapshot=html_snapshot,
    )

    if not is_trustworthy:
        reasons.extend(check_reasons)

    return (len(reasons) > 0), reasons


if __name__ == "__main__":

    SAMPLE_HTML = """
    <html><body>
      <div class="inventory_item">
        <div class="inventory_item_name">Sauce Labs Backpack</div>
        <button class="btn_inventory">Add to cart</button>
      </div>
      <div class="header_secondary_container">
        <span class="title">Products</span>
      </div>
    </body></html>
    """

    sample_bug_high_confidence = '{"bug_found": true, "description": "Checkout button clipped on mobile", "fix": "Add overflow-x: hidden", "confidence_score": 0.85, "severity_level": "Major"}'
    sample_bug_low_confidence = '{"bug_found": true, "description": "Possible contrast issue", "fix": "Consider adjusting text color", "confidence_score": 0.45, "severity_level": "Minor"}'
    sample_clean = '{"bug_found": false, "description": null, "fix": null, "confidence_score": 0.95, "severity_level": null}'
    sample_with_markdown = '```json\n{"bug_found": true, "description": "Text overlap", "fix": "Adjust z-index", "confidence_score": 0.7, "severity_level": "Minor"}\n```'
    sample_malformed = '{"bug_found": true, "description": "broken json missing closing brace"'

    # Ye do cases DOM cross-check ke liye hain — real LLaVA outputs se liye
    sample_contradictory = '{"bug_found": true, "description": "The layout seems consistent with the rest of the page.", "fix": "As no UI bugs were found, no fix is required.", "confidence_score": 0.90, "severity_level": "Minor"}'
    sample_hallucinated = '{"bug_found": true, "description": "The \'Comments field\' has a spelling issue.", "fix": "Correct the spelling.", "confidence_score": 0.85, "severity_level": "Minor"}'
    sample_verified = '{"bug_found": true, "description": "The \'Add to cart\' button is clipped and extends outside the viewport.", "fix": "Constrain the button width to its container.", "confidence_score": 0.88, "severity_level": "Major"}'

    print("High-confidence bug:")
    r1 = parse_vlm_response(sample_bug_high_confidence)
    review1, why1 = needs_human_review(r1)
    print(f"  severity: {r1.severity_level}, confidence: {r1.confidence_score}, needs review: {review1}")
    for w in why1:
        print(f"    - {w}")

    print("\nLow-confidence bug:")
    r2 = parse_vlm_response(sample_bug_low_confidence)
    review2, why2 = needs_human_review(r2)
    print(f"  severity: {r2.severity_level}, confidence: {r2.confidence_score}, needs review: {review2}")
    for w in why2:
        print(f"    - {w}")

    print("\nClean report:")
    r3 = parse_vlm_response(sample_clean)
    review3, why3 = needs_human_review(r3)
    print(f"  bug_found: {r3.bug_found}, needs review: {review3}")

    print("\nResponse with markdown fences (should still parse):")
    r4 = parse_vlm_response(sample_with_markdown)
    print(f"  parsed successfully: {r4 is not None}")
    if r4:
        print(f"  description: {r4.description}")

    print("\nMalformed JSON (should fail gracefully, not crash):")
    r5 = parse_vlm_response(sample_malformed)
    print(f"  result: {r5} (None means it was skipped safely)")

    # ---------- DOM cross-check cases ----------

    print("\n--- DOM cross-check (with HTML snapshot) ---")

    print("\nSelf-contradictory report (real LLaVA output):")
    r6 = parse_vlm_response(sample_contradictory)
    review6, why6 = needs_human_review(r6, html_snapshot=SAMPLE_HTML)
    print(f"  needs review: {review6}")
    for w in why6:
        print(f"    - {w}")

    print("\nHallucinated element:")
    r7 = parse_vlm_response(sample_hallucinated)
    review7, why7 = needs_human_review(r7, html_snapshot=SAMPLE_HTML)
    print(f"  needs review: {review7}")
    for w in why7:
        print(f"    - {w}")

    print("\nGenuine bug — element verified in DOM:")
    r8 = parse_vlm_response(sample_verified)
    review8, why8 = needs_human_review(r8, html_snapshot=SAMPLE_HTML)
    print(f"  needs review: {review8}")
    for w in why8:
        print(f"    - {w}")