"""
Stage 2 integration test — DOM cross-check against REAL HTML snapshots
captured by Playwright (frontend branch, screenshots/).

Ye confirm karta hai ki dom_check.py dummy HTML ke bajaye asli
saucedemo markup pe bhi kaam karta hai.

Run from backend/app:
    python test_dom_integration.py
"""

import os
from validators.dom_check import validate_report

# backend/app -> repo root
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

SNAPSHOTS = {
    "broken": os.path.join(REPO_ROOT, "screenshots", "broken", "broken-button-clip.html"),
    "product": os.path.join(REPO_ROOT, "screenshots", "clean", "product-page.html"),
    "cart": os.path.join(REPO_ROOT, "screenshots", "clean", "cart-multi-item.html"),
}


def load(key):
    path = SNAPSHOTS[key]
    if not os.path.exists(path):
        print(f"MISSING: {path}")
        return None
    with open(path, encoding="utf-8") as f:
        return f.read()


def run(label, report, html, should_pass):
    ok, reasons = validate_report(report, html)
    verdict = "PASS" if ok == should_pass else "FAIL"
    status = "TRUSTWORTHY" if ok else "BLOCKED"

    print(f"\n[{verdict}] {label}")
    print(f"   result: {status}   (expected: {'TRUSTWORTHY' if should_pass else 'BLOCKED'})")
    for r in reasons:
        print(f"   - {r}")
    return verdict == "PASS"


if __name__ == "__main__":

    broken_html = load("broken")
    product_html = load("product")
    cart_html = load("cart")

    if not all([broken_html, product_html, cart_html]):
        print("\nSnapshots missing. Run:")
        print("  git checkout origin/frontend -- screenshots/")
        raise SystemExit(1)

    print(f"Loaded snapshots: broken={len(broken_html)} chars, "
          f"product={len(product_html)} chars, cart={len(cart_html)} chars")

    results = []

    # 1. Genuine bug — 'Add to cart' asli DOM mein hai
    results.append(run(
        "Genuine bug — quoted element exists in broken page",
        {
            "bug_found": True,
            "description": "The 'Add to cart' button overflows the viewport and is clipped.",
            "fix": "Constrain the button width to its container.",
            "confidence_score": 0.88,
            "severity_level": "Major",
        },
        broken_html,
        should_pass=True,
    ))

    # 2. Hallucination — 'Comments field' kahin nahi hai (real LLaVA output)
    results.append(run(
        "Hallucinated element — 'Comments field'",
        {
            "bug_found": True,
            "description": "The 'Comments field' has a spelling issue.",
            "fix": "Correct the spelling.",
            "confidence_score": 0.85,
            "severity_level": "Minor",
        },
        product_html,
        should_pass=False,
    ))

    # 3. Self-contradiction (real LLaVA output)
    results.append(run(
        "Self-contradictory report",
        {
            "bug_found": True,
            "description": "The layout seems consistent with the rest of the page.",
            "fix": "As no UI bugs were found, no fix is required.",
            "confidence_score": 0.90,
            "severity_level": "Minor",
        },
        product_html,
        should_pass=False,
    ))

    # 4. Real element on clean page — verify hona chahiye
    results.append(run(
        "Real element quoted on clean product page",
        {
            "bug_found": True,
            "description": "The 'Sauce Labs Backpack' title is misaligned.",
            "fix": "Adjust the heading margin.",
            "confidence_score": 0.75,
            "severity_level": "Minor",
        },
        product_html,
        should_pass=True,
    ))

    # 5. Clean report — checks skip hone chahiye
    results.append(run(
        "Clean report, no bug claimed",
        {
            "bug_found": False,
            "description": "No visible UI bug was detected.",
            "fix": "No fix is required.",
            "confidence_score": 0.95,
            "severity_level": None,
        },
        cart_html,
        should_pass=True,
    ))

    passed = sum(results)
    print(f"\n{'=' * 50}")
    print(f"Stage 2 integration: {passed}/{len(results)} passed")