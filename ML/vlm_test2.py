import os
import json
import re
import tempfile
import http.server
import socketserver
import threading

import ollama
from PIL import Image
from pathlib import Path
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# -------------------------------------------------
# Config
# -------------------------------------------------
MODEL = "qwen2.5vl:7b"
TILE_TRIGGER_WIDTH = 2000
NUM_TILES = 3
TILE_OVERLAP = 100
SEVERITY_RANK = {"Minor": 1, "Major": 2, "Critical": 3}
VOTE_ATTEMPTS = 3

HTML_PATH = "screenshots/broken/broken-button-clip/assets/broken-button-clip.html"
AFTER_SCREENSHOT_PATH = "ML/images/after-fix.png"
LOG_PATH = "ML/self_healing_log.json"

CROP_REGION = {
    "left": 0.0,
    "top": 0.15,
    "right": 0.35,
    "bottom": 0.55,
}

image_paths = [
    "screenshots/broken/broken-button-clip/assets/broken-button-clip.png",
    "screenshots/clean/product-page/assets/product-page.png",
    "screenshots/clean/cart-multi-item/assets/cart-multi-item.png",
    "screenshots/clean/confirmation-page/assets/confirmation-page.png",
]

HTML_FOR_IMAGE = {
    "screenshots/broken/broken-button-clip/assets/broken-button-clip.png": "screenshots/broken/broken-button-clip/assets/broken-button-clip.html",
    "screenshots/clean/product-page/assets/product-page.png": "screenshots/clean/product-page/assets/product-page.html",
    "screenshots/clean/cart-multi-item/assets/cart-multi-item.png": "screenshots/clean/cart-multi-item/assets/cart-multi-item.html",
    "screenshots/clean/confirmation-page/assets/confirmation-page.png": "screenshots/clean/confirmation-page/assets/confirmation-page.html",
}

REQUIRED_FIELDS = [
    "bug_found",
    "description",
    "severity_level",
    "confidence_score",
    "fix",
]

BUG_INDICATOR_PHRASES = [
    "cut off", "cut-off", "clipped", "clipping", "hidden", "not visible",
    "overflow", "overflowing", "stretched", "broken", "truncated",
    "overlapping", "misaligned", "obscured", "not fully visible",
]

UNRELATED_SELECTOR_KEYWORDS = [
    "burger", "bm-burger", "menu_button", "hamburger",
    "primary_header", "header_container", "nav_",
]


# -------------------------------------------------
# Week 4: Image Cropping
# -------------------------------------------------
def crop_to_product_card(img_path, temp_dir):
    with Image.open(img_path) as im:
        im = im.convert("RGB")
        width, height = im.size

        left = int(width * CROP_REGION["left"])
        top = int(height * CROP_REGION["top"])
        right = int(width * CROP_REGION["right"])
        bottom = int(height * CROP_REGION["bottom"])

        cropped = im.crop((left, top, right, bottom))

        crop_path = os.path.join(temp_dir, "product_card_crop.png")
        cropped.save(crop_path)

        print(f"   Cropped to product-card region: {right - left}x{bottom - top} "
              f"(from {width}x{height})")

        return crop_path


# -------------------------------------------------
# HTML Loader
# -------------------------------------------------
def load_page_html(img_path, max_chars=8000):
    html_file = HTML_FOR_IMAGE.get(img_path)
    if not html_file:
        print(f"   ⚠️  No HTML mapped for {img_path} - selector will be null")
        return ""
    if not Path(html_file).exists():
        print(f"   ⚠️  HTML file missing: {html_file}")
        return ""
    return Path(html_file).read_text(encoding="utf-8", errors="ignore")[:max_chars]


# -------------------------------------------------
# Vision Audit Prompt
# -------------------------------------------------
def build_prompt(page_html):
    html_block = page_html if page_html else "(HTML not available for this screenshot)"
    return f"""You are an expert QA Automation Visual Auditor.
Examine this UI screenshot carefully for visual bugs.

This image has been cropped to show ONLY the first product card in the
product listing area, so you do not need to worry about the page header,
navigation, or hamburger menu - they are not in this image at all.

Here is the page HTML for this screenshot:
```html
{html_block}
```

LOOK SPECIFICALLY FOR:
- Horizontal layout overflow or stretched/clipped button borders
- Broken, unreadable, or truncated button controls
- Overlapping text, misplaced grids, or misaligned containers

RULES:
1. If you see ANY stretched element, overflowing box, clipped or cut-off
   button, or broken button border in this cropped image, set
   "bug_found": true. Judge this from the image itself, not from the HTML.
2. If "bug_found" is true:
   - "description" MUST name the exact element affected and describe the
     visual defect you can actually see.
   - "severity_level" MUST be "Critical" (blocks the user), "Major"
     (clearly broken but usable), or "Minor" (cosmetic only).
     Choose based on real impact. Do not default to one value.
   - "confidence_score" MUST reflect how clearly you can see the defect.
     Use a value between 0.0 and 1.0. Do not always return the same number.
   - "fix" MUST be a JSON object (not a sentence) with this exact shape,
     kept SHORT - the selector must be at most 6 parts long:
     {{
       "selector": "<short selector, max 6 space-separated parts>",
       "css_changes": [
         {{"property": "<a real CSS property name>", "value": "<a valid CSS value>"}}
       ],
       "explanation": "<one short sentence of why this fixes it>"
     }}
3. SELECTOR RULES (strict):
   - The selector MUST match an element that actually exists in the HTML above.
   - The selector MUST be SHORT: at most 6 space-separated parts. Never
     repeat the same class name more than once in a selector.
   - The selector MUST come from the product card visible in THIS image.
     Do NOT combine class names from different, unrelated parts of the
     page (e.g. never mix a navigation/header/menu class with a
     product-card class in the same selector - they are never the same
     element, and the navigation is not even visible in this crop).
   - Prefer the element's id, written as "#the-id".
   - If it has no id, use its exact class exactly as spelled in the HTML.
   - Do NOT invent, guess, abbreviate, or translate selectors.
   - If the class you want to use appears on MORE THAN ONE element in the
     HTML, combine it with a positional pseudo-class (":first-child",
     ":nth-child(n)") on the closest matching parent container so the
     selector points to exactly ONE element - built from the ACTUAL
     class names in the HTML above, never copy any class name from
     these instructions.
   - If the class in the HTML above is NOT repeated, use that class
     directly - do NOT add a positional pseudo-class when not needed.
   - If the HTML is not available, or you cannot find the element in it,
     set "selector" to null and "css_changes" to [].
4. The fix must REDUCE the defect. If an element is clipped or cut off,
   do not shrink it. Only include properties that directly address the
   defect (width, max-width, overflow, white-space, display, position).
   Maximum 3 property changes.
   If clipped/cut off: do NOT shrink it, RELAX it instead. For a clipped
   button always include all three: width:auto, max-width:none,
   overflow:visible. Only shrink width/max-width when the element is too
   LARGE and overlapping other elements (opposite case).
5. If no visible defects: "bug_found": false, "severity_level": null,
   "description": "No visible UI bug was detected.",
   "fix": {{"selector": null, "css_changes": [], "explanation": "No fix required."}}

Return ONLY raw JSON. No markdown, no backticks, no commentary.
Schema (types only - do not copy these placeholder values):
{{
  "bug_found": <boolean>,
  "description": "<string>",
  "severity_level": "<Critical|Major|Minor or null>",
  "confidence_score": <number between 0.0 and 1.0>,
  "fix": {{
    "selector": "<string or null>",
    "css_changes": [
      {{"property": "<string>", "value": "<string>"}}
    ],
    "explanation": "<string>"
  }}
}}
"""

# -------------------------------------------------
# Tiling Logic (fallback, unused when cropping is active)
# -------------------------------------------------
def make_tiles(img_path, temp_dir):
    with Image.open(img_path) as im:
        im = im.convert("RGB")
        width, height = im.size
        print(f"   Image size: {width} x {height}")
        if width <= TILE_TRIGGER_WIDTH:
            print("   Tiling not needed (image is small enough)")
            return [("full", img_path)]
        step = width // NUM_TILES
        tiles = []
        for i in range(NUM_TILES):
            left = max(0, i * step - TILE_OVERLAP)
            right = min(width, (i + 1) * step + TILE_OVERLAP)
            crop = im.crop((left, 0, right, height))
            tile_path = os.path.join(temp_dir, f"tile_{i + 1}.png")
            crop.save(tile_path)
            label = f"tile {i + 1}/{NUM_TILES} (x: {left}-{right})"
            tiles.append((label, tile_path))
        print(f"   Split into {NUM_TILES} overlapping tiles")
        return tiles


# -------------------------------------------------
# Ollama Runner
# -------------------------------------------------
def run_vlm(img_path, page_html):
    response = ollama.chat(
        model=MODEL,
        format="json",
        options={"num_ctx": 16384, "temperature": 0.1, "num_predict": 500},
        messages=[
            {
                "role": "user",
                "content": build_prompt(page_html),
                "images": [img_path],
            }
        ],
    )
    return response["message"]["content"]


# -------------------------------------------------
# Output Sanitization
# -------------------------------------------------
def clean_json_text(raw_output):
    text = raw_output.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text).strip()
    return text


# -------------------------------------------------
# Schema Validation
# -------------------------------------------------
def validate_result(result):
    missing = [f for f in REQUIRED_FIELDS if f not in result]
    if missing:
        print("   ❌ Missing fields:", missing)
        return None

    extra = set(result.keys()) - set(REQUIRED_FIELDS)
    if extra:
        print("   ❌ Unexpected fields:", extra)
        return None

    if not isinstance(result["bug_found"], bool):
        print("   ❌ bug_found must be true or false")
        return None

    if not isinstance(result["description"], str):
        print("   ❌ description must be a string")
        return None

    fix = result.get("fix")
    if not isinstance(fix, dict):
        print("   ❌ fix must be an object")
        return None

    if result["bug_found"]:
        if result["severity_level"] not in SEVERITY_RANK:
            print("   ❌ Invalid severity_level (need Critical/Major/Minor)")
            return None

        selector = fix.get("selector")
        changes = fix.get("css_changes")

        if selector is None:
            if changes not in ([], None):
                print("   ❌ css_changes must be empty when selector is null")
                return None
            fix["css_changes"] = []
            print("   ⚠️  Bug reported but no selector found in HTML")
        else:
            if not isinstance(selector, str) or not selector.strip():
                print("   ❌ fix.selector must be a non-empty string or null")
                return None

            if not isinstance(changes, list) or len(changes) == 0:
                print("   ❌ fix.css_changes must be a non-empty list")
                return None

            for c in changes:
                if not isinstance(c, dict) or "property" not in c or "value" not in c:
                    print("   ❌ each css_changes item needs 'property' and 'value'")
                    return None
                if not isinstance(c["property"], str) or not isinstance(c["value"], str):
                    print("   ❌ property/value must be strings")
                    return None
    else:
        if result["severity_level"] is not None:
            print("   ❌ severity_level must be null when bug_found is false")
            return None
        if fix.get("selector") is not None or fix.get("css_changes") != []:
            print("   ❌ fix must be null/empty when bug_found is false")
            return None

    try:
        result["confidence_score"] = float(result["confidence_score"])
    except (ValueError, TypeError):
        print("   ❌ Invalid confidence_score")
        return None

    if not 0.0 <= result["confidence_score"] <= 1.0:
        print("   ❌ confidence_score must be between 0.0 and 1.0")
        return None

    return result


# -------------------------------------------------
# Apply CSS Fix
# -------------------------------------------------
def apply_css_fix(html_path, fix):
    html_path = Path(html_path)
    if not html_path.exists():
        raise FileNotFoundError(f"HTML file not found: {html_path}")

    soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "html.parser")

    selector = fix.get("selector")
    changes = fix.get("css_changes", [])

    if not selector:
        raise ValueError("Fix has no selector - nothing to apply")

    element = soup.select_one(selector)
    if element is None:
        raise ValueError(f"SELECTOR_NOT_FOUND: no element matches '{selector}'")

    existing_style = element.get("style", "")
    style_dict = {}
    for item in existing_style.split(";"):
        if ":" in item:
            k, v = item.split(":", 1)
            style_dict[k.strip()] = v.strip()

    for change in changes:
        style_dict[change["property"]] = change["value"]

    element["style"] = "; ".join(f"{k}: {v}" for k, v in style_dict.items())

    html_path.write_text(str(soup), encoding="utf-8")
    print(f"   ✅ CSS fix applied to: {selector}")


# -------------------------------------------------
# Screenshot HTML
# -------------------------------------------------
def screenshot_html(html_path, screenshot_path):
    html_path = Path(html_path).resolve()
    screenshot_path = Path(screenshot_path).resolve()
    screenshot_path.parent.mkdir(parents=True, exist_ok=True)
    serve_dir = html_path.parent

    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(serve_dir), **kwargs)

    httpd = socketserver.TCPServer(("localhost", 0), QuietHandler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            page = browser.new_page(viewport={"width": 1920, "height": 1080})
            page.on("console", lambda msg: print(f"   CONSOLE: {msg.text}"))
            page.on("pageerror", lambda err: print(f"   PAGE ERROR: {err}"))
            page.on("requestfailed", lambda req: print(f"   REQUEST FAILED: {req.url} - {req.failure}"))
            page.goto(f"http://localhost:{port}/{html_path.name}")
            page.wait_for_timeout(5000)
            page.screenshot(path=str(screenshot_path), full_page=False)
            browser.close()
    finally:
        httpd.shutdown()
        httpd.server_close()

    print(f"   ✅ Screenshot saved: {screenshot_path}")


# -------------------------------------------------
# Screenshot Sanity Check
# -------------------------------------------------
def verify_bug_screenshot(html_path):
    html_path = Path(html_path).resolve()
    serve_dir = html_path.parent

    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(serve_dir), **kwargs)

    httpd = socketserver.TCPServer(("localhost", 0), QuietHandler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1920, "height": 1080})
            page.goto(f"http://localhost:{port}/{html_path.name}")
            page.wait_for_timeout(3000)

            button = page.query_selector(".inventory_item:first-child .btn_inventory")
            if button is None:
                print("   ⚠️  [Screenshot check] Target button not found in rendered DOM")
                browser.close()
                return False

            box = button.bounding_box()
            browser.close()

            if box is None or box["width"] <= 0:
                print("   ⚠️  [Screenshot check] Target button has zero size - page may not have rendered correctly")
                return False

            print(f"   ✅ [Screenshot check] Target button rendered, width={box['width']:.0f}px")
            return True
    finally:
        httpd.shutdown()
        httpd.server_close()


# -------------------------------------------------
# Evaluation of After-Fix Screenshot
# -------------------------------------------------
def evaluate_fixed_screenshot(image_path, original_bug):
    eval_prompt = """You are a QA Visual Auditor. Look ONLY at the screenshot
below - ignore any prior description or label, and judge fresh from what
you can actually see right now in the image.

Independently inspect the button in this screenshot and answer: is any
letter or word of its text cut off, hidden, or unreadable? Is any part of
its border missing or clipped by the edge of another box?

If you can read every word of the button's text completely, and its
border forms a full rectangle with nothing sliced off - the answer is
that there is NO bug, regardless of what any earlier note claimed.

Do not assume a bug is present just because you were told one existed
before. Verify it yourself from the pixels you see now.

Set "bug_still_present" to false if the full button and its full text are
visible and readable. Set it to true only if something is still visibly
cut off or hidden RIGHT NOW in this image.

"confidence_score" must reflect how clearly you can tell. Use a value
between 0.0 and 1.0. Do not always return the same number.

Return ONLY raw JSON. No markdown, no backticks, no commentary.
Schema (types only - do not copy these placeholder values):
{
  "bug_still_present": <boolean>,
  "confidence_score": <number between 0.0 and 1.0>,
  "explanation": "<string>"
}
"""

    response = ollama.chat(
        model=MODEL,
        format="json",
        options={"num_ctx": 16384, "temperature": 0.1, "num_predict": 500},
        messages=[
            {
                "role": "user",
                "content": eval_prompt,
                "images": [image_path],
            }
        ],
    )

    raw = response["message"]["content"]
    cleaned = clean_json_text(raw)
    return json.loads(cleaned)


# -------------------------------------------------
# Selector Guard
# -------------------------------------------------
def sanity_check_selector(fix: dict) -> tuple[bool, str]:
    selector = (fix.get("selector") or "").lower()

    if not selector:
        return False, "Selector is empty."

    if len(selector) > 250:
        return False, f"Selector is suspiciously long ({len(selector)} chars) - likely a runaway/looped generation."

    matched = [kw for kw in UNRELATED_SELECTOR_KEYWORDS if kw in selector]
    if matched:
        return False, (
            f"Selector contains unrelated navigation/menu keywords {matched} "
            f"combined with a product-card path — likely hallucinated by mixing "
            f"two unrelated DOM branches."
        )

    return True, ""


# -------------------------------------------------
# Contradiction Guard
# -------------------------------------------------
def sanity_check_evaluation(evaluation: dict) -> dict:
    explanation = (evaluation.get("explanation") or "").lower()
    bug_still_present = evaluation.get("bug_still_present", False)

    if not bug_still_present:
        matched = [p for p in BUG_INDICATOR_PHRASES if p in explanation]
        if matched:
            print(
                f"   ⚠️  Contradiction detected: bug_still_present=False but "
                f"explanation mentions {matched}. Overriding to True (fail-safe)."
            )
            evaluation = dict(evaluation)
            evaluation["bug_still_present"] = True
            evaluation["contradiction_flagged"] = True
            evaluation["contradiction_reason"] = f"Explanation contains: {matched}"

    return evaluation


# -------------------------------------------------
# Logging
# -------------------------------------------------
def log_self_healing_result(entry):
    log_file = Path(LOG_PATH)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    logs = []
    if log_file.exists():
        try:
            logs = json.loads(log_file.read_text())
        except json.JSONDecodeError:
            logs = []
    logs.append(entry)
    log_file.write_text(json.dumps(logs, indent=2))


# -------------------------------------------------
# Execute Tile Analysis
# -------------------------------------------------
def analyze_tile(label, tile_path, page_html):
    print(f"\n   ----- {label} -----")

    try:
        raw_output = run_vlm(tile_path, page_html)
    except Exception as e:
        print(f"   ❌ VLM error: {e}")
        return None

    print("   Raw model output:")
    print("   " + raw_output.strip().replace("\n", "\n   "))

    cleaned = clean_json_text(raw_output)

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as e:
        print("   ❌ Model did not return valid JSON")
        print("   JSON Error:", e)
        return None

    return validate_result(parsed)


# -------------------------------------------------
# Merge Results
# -------------------------------------------------
def merge_results(tile_results):
    valid = [r for r in tile_results if r is not None]

    if not valid:
        return None

    bugs = [r for r in valid if r["bug_found"]]

    if not bugs:
        lowest = min(valid, key=lambda r: r["confidence_score"])
        return {
            "bug_found": False,
            "description": "No visible UI bug was detected in this screenshot.",
            "severity_level": None,
            "confidence_score": lowest["confidence_score"],
            "fix": {"selector": None, "css_changes": [], "explanation": "No fix required."},
        }

    actionable = [b for b in bugs if b["fix"].get("selector")]
    pool = actionable if actionable else bugs

    worst = max(
        pool,
        key=lambda r: (SEVERITY_RANK[r["severity_level"]], r["confidence_score"]),
    )

    return {
        "bug_found": True,
        "description": worst["description"],
        "severity_level": worst["severity_level"],
        "confidence_score": worst["confidence_score"],
        "fix": worst["fix"],
    }


# -------------------------------------------------
# Run one screenshot through the audit (CROPPING ACTIVE)
# -------------------------------------------------
def audit_image(img):
    page_html = load_page_html(img)

    with tempfile.TemporaryDirectory() as temp_dir:
        cropped_path = crop_to_product_card(img, temp_dir)
        tile_results = [analyze_tile("cropped-product-card", cropped_path, page_html)]
        return merge_results(tile_results)


# -------------------------------------------------
# Reliability Wrapper
# -------------------------------------------------
def audit_image_reliable(img, attempts=VOTE_ATTEMPTS):
    results = [audit_image(img) for _ in range(attempts)]
    valid = [r for r in results if r is not None]

    if not valid:
        return None

    bug_votes = [r for r in valid if r["bug_found"]]
    clean_votes = [r for r in valid if not r["bug_found"]]

    print(f"   [Reliability check] {len(bug_votes)}/{len(valid)} runs said BUG_FOUND")

    if len(bug_votes) > len(clean_votes):
        return max(bug_votes, key=lambda r: r["confidence_score"])
    elif len(clean_votes) > len(bug_votes):
        return clean_votes[0]
    else:
        print("   [Reliability check] Tie vote — defaulting to BUG_FOUND (fail-safe)")
        return bug_votes[0] if bug_votes else clean_votes[0]


# -------------------------------------------------
# Main Execution
# -------------------------------------------------
if __name__ == "__main__":

    bug_screenshot = "screenshots/broken/broken-button-clip/assets/broken-button-clip.png"

    if os.path.exists(HTML_PATH):
        print(f"Refreshing {bug_screenshot} from current {HTML_PATH} ...")
        screenshot_html(HTML_PATH, bug_screenshot)

        print("\nVerifying the broken-button HTML actually renders the bug...")
        if not verify_bug_screenshot(HTML_PATH):
            print("⚠️  WARNING: the target button did not render as expected. "
                  "VLM results for this image may be unreliable.")
    else:
        print(f"⚠️  {HTML_PATH} not found — skipping screenshot refresh")

    for img in image_paths:

        if not os.path.exists(img):
            print(f"\n⚠️ Skipping {img}: File not found!")
            continue

        print(f"\n==================== Testing: {img} ====================")

        try:
            final = audit_image_reliable(img)

            print("\n   ===== MERGED RESULT =====")

            if final is None:
                print("\n❌ No valid result from any tile")
                continue

            print("\n✅ Valid JSON:")
            print(json.dumps(final, indent=2))

            if final["bug_found"]:
                print("\n🔴 BUG DETECTED")
            else:
                print("\n🟢 NO BUG DETECTED")

        except Exception as e:
            print(f"\n❌ Error: {e}")

    print("\n\n==================== SELF-HEALING LOOP ====================")

    if not os.path.exists(bug_screenshot):
        print(f"⚠️ Skipping self-healing: {bug_screenshot} not found")

    else:
        detection = audit_image_reliable(bug_screenshot)

        if detection is None or not detection["bug_found"]:
            print("🟢 No bug detected - nothing to fix")

        elif not detection["fix"].get("selector"):
            print("⚠️ Bug detected but no valid selector found in HTML - cannot auto-fix")
            print(json.dumps(detection, indent=2))
            log_self_healing_result({
                "html_path": HTML_PATH,
                "original_bug": detection["description"],
                "fix_applied": None,
                "status": "NO_SELECTOR",
                "evaluation": None,
            })

        else:
            fix = detection["fix"]

            print("\n1. Applying fix:")
            print(json.dumps(fix, indent=2))

            is_valid, reason = sanity_check_selector(fix)

            if not is_valid:
                print(f"⚠️  Selector rejected before apply: {reason}")
                log_self_healing_result({
                    "html_path": HTML_PATH,
                    "original_bug": detection["description"],
                    "fix_applied": fix,
                    "status": "BAD_SELECTOR",
                    "evaluation": None,
                    "error": reason,
                })
                print("\n==============================")
                print("SELF-HEALING RESULT: BAD_SELECTOR")
                print("==============================")

            else:
                try:
                    apply_css_fix(HTML_PATH, fix)

                    print("\n2. Taking after-fix screenshot...")
                    screenshot_html(HTML_PATH, AFTER_SCREENSHOT_PATH)

                    print("\n3. Evaluating fixed screenshot...")
                    evaluation = evaluate_fixed_screenshot(
                        AFTER_SCREENSHOT_PATH,
                        detection["description"],
                    )
                    evaluation = sanity_check_evaluation(evaluation)
                    print(json.dumps(evaluation, indent=2))

                    status = "NOT_FIXED" if evaluation.get("bug_still_present") else "FIXED"

                    log_self_healing_result({
                        "html_path": HTML_PATH,
                        "original_bug": detection["description"],
                        "fix_applied": fix,
                        "status": status,
                        "evaluation": evaluation,
                    })

                    print("\n==============================")
                    print(f"SELF-HEALING RESULT: {status}")
                    print("==============================")

                except Exception as e:
                    print(f"❌ Self-healing error: {e}")

                    log_self_healing_result({
                        "html_path": HTML_PATH,
                        "original_bug": detection["description"],
                        "fix_applied": fix,
                        "status": "APPLY_FAILED",
                        "evaluation": None,
                        "error": str(e),
                    })

                    print("\n==============================")
                    print("SELF-HEALING RESULT: APPLY_FAILED")
                    print("==============================")
                    