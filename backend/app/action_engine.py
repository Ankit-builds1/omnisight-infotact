"""
Action Engine — OmniSight Backend

Parses the VLM's JSON response and extracts the bug report fields,
validating against the VLMBugReport schema (see schemas/vlm_output.py).

Week 2, Day 2: basic parsing of bug_found, description, fix.
Day 3 will add confidence_score and severity_level extraction + validation.
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

    return report


if __name__ == "__main__":
    sample_bug = '{"bug_found": true, "description": "Checkout button clipped on mobile", "fix": "Add overflow-x: hidden", "confidence_score": 0.85, "severity_level": "Major"}'
    sample_clean = '{"bug_found": false, "description": null, "fix": null, "confidence_score": 0.95, "severity_level": null}'

    print("Testing with a bug report:")
    result = parse_vlm_response(sample_bug)
    print(f"  bug_found: {result.bug_found}")
    print(f"  description: {result.description}")
    print(f"  fix: {result.fix}")

    print("\nTesting with a clean report:")
    result2 = parse_vlm_response(sample_clean)
    print(f"  bug_found: {result2.bug_found}")