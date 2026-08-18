"""
Action Engine — OmniSight Backend

Parses the VLM's JSON response and extracts the bug report fields,
validating against the VLMBugReport schema (see schemas/vlm_output.py).

Week 2, Day 2: basic parsing of bug_found, description, fix.
Week 2, Day 3: added confidence_score + severity_level extraction, plus
    validation rules (e.g. bug_found=True must have a description and fix).
Week 2, Day 4: added malformed JSON handling — retries once, then logs and
    skips gracefully instead of crashing the whole pipeline.
"""

import json
import logging
from schemas.vlm_output import VLMBugReport

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


def needs_human_review(report: VLMBugReport, threshold: float = 0.6) -> bool:
    """
    Returns True if this fix is too uncertain to auto-merge and should
    be flagged for mandatory human review instead.
    """
    return report.bug_found and report.confidence_score < threshold


if __name__ == "__main__":
    sample_bug_high_confidence = '{"bug_found": true, "description": "Checkout button clipped on mobile", "fix": "Add overflow-x: hidden", "confidence_score": 0.85, "severity_level": "Major"}'
    sample_bug_low_confidence = '{"bug_found": true, "description": "Possible contrast issue", "fix": "Consider adjusting text color", "confidence_score": 0.45, "severity_level": "Minor"}'
    sample_clean = '{"bug_found": false, "description": null, "fix": null, "confidence_score": 0.95, "severity_level": null}'
    sample_with_markdown = '```json\n{"bug_found": true, "description": "Text overlap", "fix": "Adjust z-index", "confidence_score": 0.7, "severity_level": "Minor"}\n```'
    sample_malformed = '{"bug_found": true, "description": "broken json missing closing brace"'

    print("High-confidence bug:")
    r1 = parse_vlm_response(sample_bug_high_confidence)
    print(f"  severity: {r1.severity_level}, confidence: {r1.confidence_score}, needs review: {needs_human_review(r1)}")

    print("\nLow-confidence bug:")
    r2 = parse_vlm_response(sample_bug_low_confidence)
    print(f"  severity: {r2.severity_level}, confidence: {r2.confidence_score}, needs review: {needs_human_review(r2)}")

    print("\nClean report:")
    r3 = parse_vlm_response(sample_clean)
    print(f"  bug_found: {r3.bug_found}, needs review: {needs_human_review(r3)}")

    print("\nResponse with markdown fences (should still parse):")
    r4 = parse_vlm_response(sample_with_markdown)
    print(f"  parsed successfully: {r4 is not None}")
    if r4:
        print(f"  description: {r4.description}")

    print("\nMalformed JSON (should fail gracefully, not crash):")
    r5 = parse_vlm_response(sample_malformed)
    print(f"  result: {r5} (None means it was skipped safely)")