"""
DOM cross-check layer for OmniSight Action Engine.

VLM ke output ko Playwright ke HTML snapshot ke against verify karta hai.
Do tarah ka junk pakadta hai:

  1. Self-contradictory reports — bug_found=True par description
     bolti hai "no visible UI bugs"
  2. Hallucinated elements — model aise text ka zikr karta hai jo
     page pe exist hi nahi karta

Model-agnostic: LLaVA ho ya Qwen, dono pe kaam karega.
"""

import re
from dataclasses import dataclass


# Phrases jo "koi bug nahi mila" indicate karte hain.
# bug_found=True ke saath mile -> contradiction.
NO_BUG_PHRASES = [
    "no visible ui bug",
    "no visible ui bugs",
    "no ui bugs were found",
    "no ui bugs were detected",
    "there are no visible",
    "no bugs detected",
    "layout seems consistent",
    "no fix is required",
]

# Description se quoted element text nikalta hai:
# 'Add to Cart', "Shopping Cart"
QUOTED_TEXT = re.compile(r"['\"]([^'\"]{3,40})['\"]")


@dataclass
class CheckResult:
    passed: bool
    reason: str


def _normalize(text: str) -> str:
    """Lowercase + whitespace collapse, taaki matching reliable rahe."""
    return re.sub(r"\s+", " ", text.lower()).strip()


def _strip_html(html: str) -> str:
    """HTML tags hata ke sirf visible text nikalo."""
    without_scripts = re.sub(
        r"<(script|style)[^>]*>.*?</\1>",
        " ",
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    text_only = re.sub(r"<[^>]+>", " ", without_scripts)
    return _normalize(text_only)


def check_self_consistency(report: dict) -> CheckResult:
    """
    Rule 1: bug_found=True hai par description khud keh rahi hai
    ki koi bug nahi -> reject.
    """
    if not report.get("bug_found"):
        return CheckResult(True, "No bug claimed; consistency check skipped.")

    description = _normalize(report.get("description", ""))

    for phrase in NO_BUG_PHRASES:
        if phrase in description:
            return CheckResult(
                False,
                f"Self-contradictory: bug_found=True but description "
                f"contains '{phrase}'.",
            )

    return CheckResult(True, "Description is consistent with bug_found.")


def check_against_dom(report: dict, html_snapshot: str) -> CheckResult:
    """
    Rule 2: description mein quote kiya gaya element text HTML
    snapshot mein hona chahiye. Nahi hai -> hallucination.
    """
    if not report.get("bug_found"):
        return CheckResult(True, "No bug claimed; DOM check skipped.")

    if not html_snapshot:
        return CheckResult(True, "No HTML snapshot provided; DOM check skipped.")

    page_text = _strip_html(html_snapshot)
    description = report.get("description", "")

    quoted = QUOTED_TEXT.findall(description)

    if not quoted:
        return CheckResult(
            True,
            "No quoted element text in description; nothing to verify.",
        )

    missing = [q for q in quoted if _normalize(q) not in page_text]

    if missing:
        return CheckResult(
            False,
            f"Hallucinated element(s) not present in DOM: {missing}",
        )

    return CheckResult(True, f"All quoted elements verified in DOM: {quoted}")


def validate_report(report: dict, html_snapshot: str = None):
    """
    Poora cross-check.

    Returns:
        (is_trustworthy: bool, reasons: list[str])

    Action Engine isse use kare: False mile toh PR generate mat
    karo, human review mein bhejo.
    """
    reasons = []

    consistency = check_self_consistency(report)
    reasons.append(consistency.reason)

    dom = check_against_dom(report, html_snapshot)
    reasons.append(dom.reason)

    return (consistency.passed and dom.passed), reasons


# -------------------------------------------------
# Self-test — python -m validators.dom_check
# -------------------------------------------------
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

    cases = [
        (
            "Self-contradictory (LLaVA ne actually ye diya tha)",
            {
                "bug_found": True,
                "description": "The layout seems consistent with the rest "
                               "of the page.",
                "severity_level": "Minor",
                "confidence_score": 0.90,
                "fix": "As no UI bugs were found, no fix is required.",
            },
        ),
        (
            "Hallucinated element",
            {
                "bug_found": True,
                "description": "The 'Comments field' has a spelling issue.",
                "severity_level": "Minor",
                "confidence_score": 0.85,
                "fix": "Correct the spelling.",
            },
        ),
        (
            "Genuine bug — element DOM mein hai",
            {
                "bug_found": True,
                "description": "The 'Add to cart' button is clipped and "
                               "extends outside the viewport.",
                "severity_level": "Major",
                "confidence_score": 0.88,
                "fix": "Constrain the button width to its container.",
            },
        ),
        (
            "Clean page — no bug claimed",
            {
                "bug_found": False,
                "description": "No visible UI bug was detected.",
                "severity_level": None,
                "confidence_score": 0.95,
                "fix": "No fix is required.",
            },
        ),
    ]

    for label, report in cases:
        ok, reasons = validate_report(report, SAMPLE_HTML)
        status = "TRUSTWORTHY" if ok else "BLOCKED -> human review"
        print(f"\n=== {label} ===")
        print(f"Result: {status}")
        for r in reasons:
            print(f"  - {r}")