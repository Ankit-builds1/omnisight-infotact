import os
import json
import re
import tempfile

import ollama
from PIL import Image

# -------------------------------------------------
# Config
# -------------------------------------------------
MODEL = "qwen2.5vl:7b"

TILE_TRIGGER_WIDTH = 2000
NUM_TILES = 3
TILE_OVERLAP = 100

image_paths = [
    "ML/images/broken-button-clip.png",
    "screenshots/product-page.png",
    "screenshots/cart-multi-item.png",
    "screenshots/confirmation-page.png",
    "ML/images/manual-broken-fleece.png",
]

REQUIRED_FIELDS = [
    "bug_found",
    "description",
    "severity_level",
    "confidence_score",
    "fix",
]

SEVERITY_RANK = {"Minor": 1, "Major": 2, "Critical": 3}


# -------------------------------------------------
# Vision Audit Prompt
# -------------------------------------------------
prompt = """You are an expert QA Automation Visual Auditor.
Examine this UI screenshot carefully for visual bugs.

LOOK SPECIFICALLY FOR:
- Horizontal layout overflow or stretched/clipped button borders
- Broken, unreadable, or truncated button controls
- Overlapping text, misplaced grids, or misaligned containers

RULES:
1. If you see ANY stretched element, empty overflowing box, or broken
   button border, set "bug_found": true.
2. If "bug_found" is true:
   - "severity_level" MUST be "Major" or "Critical".
   - "description" MUST name the exact element affected and describe the
     visual defect you can acthually see.
   - "fix" MUST be a JSON object (not a sentence) with this exact shape:
     {
       "selector": "<a plausible CSS selector for the broken element, e.g. '.buy-button' or 'button.checkout'>",
       "css_changes": [
         {"property": "<a real CSS property name>", "value": "<a valid CSS value>"}
       ],
       "explanation": "<one short sentence of why this fixes it>"
     }
     Only include properties that directly address the visual defect
     (e.g. width, max-width, overflow, white-space, display, position).
     Do not include more than 3 property changes.
3. If no visible defects, set "bug_found": false, "severity_level": null,
   "description": "No visible UI bug was detected.",
   "fix": {"selector": null, "css_changes": [], "explanation": "No fix required."}

Return ONLY raw JSON matching this schema:
{
  "bug_found": true,
  "description": "string",
  "severity_level": "Major",
  "confidence_score": 0.95,
  "fix": {
    "selector": "string",
    "css_changes": [
      {"property": "string", "value": "string"}
    ],
    "explanation": "string"
  }
}
When bug_found is false, "fix" MUST be:
  {"selector": null, "css_changes": [], "explanation": "No fix required."}
"""

# -------------------------------------------------
# Tiling Logic
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
# num_ctx=8192 required - default 4096 caused image tokens
# to overflow, making the model respond without seeing the image
# -------------------------------------------------
def run_vlm(img_path):
    response = ollama.chat(
        model=MODEL,
        format="json",
        options={
            "num_ctx": 8192
        },
        messages=[
            {
                "role": "user",
                "content": prompt,
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

        if not isinstance(fix.get("selector"), str) or not fix["selector"].strip():
            print("   ❌ fix.selector must be a non-empty string")
            return None

        changes = fix.get("css_changes")
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
# Execute Tile Analysis
# -------------------------------------------------
def analyze_tile(label, tile_path):
    print(f"\n   ----- {label} -----")

    try:
        raw_output = run_vlm(tile_path)
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

    worst = max(
        bugs,
        key=lambda r: (
            SEVERITY_RANK[r["severity_level"]],
            r["confidence_score"],
        ),
    )

    return {
        "bug_found": True,
        "description": worst["description"],
        "severity_level": worst["severity_level"],
        "confidence_score": worst["confidence_score"],
        "fix": worst["fix"],
    }


# -------------------------------------------------
# Main Execution
# -------------------------------------------------
if __name__ == "__main__":
    for img in image_paths:
        if not os.path.exists(img):
            print(f"\n⚠️ Skipping {img}: File not found!")
            continue

        print(f"\n==================== Testing: {img} ====================")

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                tiles = make_tiles(img, temp_dir)

                tile_results = []
                for label, tile_path in tiles:
                    tile_results.append(analyze_tile(label, tile_path))

                final = merge_results(tile_results)

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
