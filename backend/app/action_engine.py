"""
Action Engine — OmniSight Backend

Parses the VLM's JSON response and extracts the bug report fields,
validating against the VLMBugReport schema (see schemas/vlm_output.py).

Week 2, Day 2: basic parsing of bug_found, description, fix.
Week 2, Day 3: added confidence_score + severity_level extraction, plus
    validation rules (e.g. bug_found=True must have a description and fix).
Day 4 will add malformed JSON handling (retry/skip logic).
"""

import json
from schemas.vlm_output import VLMBugReport


def parse_vlm_response(raw_response: str) -> VLMBugReport:
    """
    Takes the raw JSON string returned by the VLM and parses it into
    a validated VLMBugReport object.

    Raises ValueError if the response is not valid JSON or doesn't
    match the expected schema.
    """
    try:
        data = json.loads(raw_response)
    except json.JSONDecodeError as e:
        raise ValueError(f"VLM response is not valid JSON: {e}")

    try:
        report = VLMBugReport(**data)
    except Exception as e:
        raise ValueError(f"VLM response does not match expected schema: {e}")

    _validate_business_rules(report)

    return report


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

    print("High-confidence bug:")
    r1 = parse_vlm_response(sample_bug_high_confidence)
    print(f"  severity: {r1.severity_level}, confidence: {r1.confidence_score}, needs review: {needs_human_review(r1)}")

    print("\nLow-confidence bug:")
    r2 = parse_vlm_response(sample_bug_low_confidence)
    print(f"  severity: {r2.severity_level}, confidence: {r2.confidence_score}, needs review: {needs_human_review(r2)}")

    print("\nClean report:")
    r3 = parse_vlm_response(sample_clean)
    print(f"  bug_found: {r3.bug_found}, needs review: {needs_human_review(r3)}")