import os
import json
import re
import tempfile

import ollama
from PIL import Image

# -------------------------------------------------
# Config
# -------------------------------------------------
MODEL = "qwen2.5vl:3b"
# Agar image isse chaudi hai to tiling hoga
TILE_TRIGGER_WIDTH = 1920

# Kitne horizontal tiles banane hain
NUM_TILES = 3

# Tiles ke beech overlap (px) - taaki border pe koi bug na chhoote
TILE_OVERLAP = 100

image_paths = [
    "ML/images/broken-button-clip.png",
    "screenshots/product-page.png",
    "screenshots/cart-multi-item.png",
    "screenshots/confirmation-page.png",
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
prompt = """
Analyze this UI screenshot and determine whether there is a visible UI bug.

This image may be a horizontal SLICE of a larger page screenshot.
Judge only what is visible in this slice. Content being cut off at the
left or right edge of the slice is NOT a bug by itself - that is just
where the slice ends.

Check specifically for:
- buttons or elements that overflow, are clipped, or pushed off-screen
- incorrect button labels
- spelling mistakes
- capitalization problems
- alignment problems
- spacing problems
- overlapping elements
- missing or broken UI elements
- inconsistent fonts or styles
- obvious layout problems

Only report a bug when there is clear visible evidence.
Do not invent or assume bugs. If unsure, report bug_found as false.

Return ONLY one valid JSON object.
Do NOT use markdown.
Do NOT use ```json.
Do NOT add any explanation outside the JSON.

The JSON must contain exactly these fields:

{
  "bug_found": true,
  "description": "Clear description of the detected UI bug.",
  "severity_level": "Minor",
  "confidence_score": 0.95,
  "fix": "Clear suggested fix for the detected UI bug."
}

Rules:

1. bug_found must be either true or false.

2. If bug_found is true:
   - description must clearly describe the visible bug.
   - severity_level must be exactly one of: "Critical", "Major", "Minor"
   - confidence_score must be a decimal between 0.0 and 1.0.
   - fix must explain how to correct the bug.

3. If bug_found is false:
   - description must say that no visible UI bug was detected.
   - severity_level must be null.
   - confidence_score must be a decimal between 0.0 and 1.0.
   - fix must say that no fix is required.

4. Never use confidence values such as 90 or 95. Use 0.90 or 0.95.

5. Base the result only on visible evidence in the screenshot.

6. Return ONLY the JSON object.

7. severity_level guidance:
   - "Critical": the element is unusable or blocks the user flow entirely
   - "Major": the element is significantly clipped, overlapping, or pushed off-screen
   - "Minor": cosmetic spacing, alignment, or styling issue only

8. Quote the affected element's text EXACTLY as it appears in the screenshot,
   inside single quotes. Do not paraphrase or reconstruct names from memory.
   If you cannot read the element's text clearly, set bug_found to false.

9. This image may contain multiple similar UI elements (product cards, buttons,
   rows). Report a bug ONLY for the specific element that visibly differs from
   the others around it. If all similar elements look consistent with each
   other, set bug_found to false.
"""


# -------------------------------------------------
# Tiling: image ko overlapping horizontal slices me kaato
# -------------------------------------------------
def make_tiles(img_path, temp_dir):
    """
    Returns list of (label, path).
    Agar image chhoti hai to original hi single tile ke roop me return.
    """
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

            tile_path = os.path.join(
                temp_dir,
                f"tile_{i + 1}.png"
            )
            crop.save(tile_path)

            label = f"tile {i + 1}/{NUM_TILES} (x: {left}-{right})"
            tiles.append((label, tile_path))

        print(f"   Split into {NUM_TILES} overlapping tiles")
        return tiles


# -------------------------------------------------
# Ek image (ya tile) ko VLM me bhejo
# -------------------------------------------------
def run_vlm(img_path):
    response = ollama.chat(
        model=MODEL,
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
# Markdown fences hatao
# -------------------------------------------------
def clean_json_text(raw_output):
    text = raw_output.strip()

    text = re.sub(
        r"^```(?:json)?\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(r"\s*```$", "", text).strip()

    return text


# -------------------------------------------------
# Schema validation - valid dict ya None return karta hai
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

    if not isinstance(result["fix"], str):
        print("   ❌ fix must be a string")
        return None

    if result["bug_found"]:
        if result["severity_level"] not in SEVERITY_RANK:
            print("   ❌ Invalid severity_level (need Critical/Major/Minor)")
            return None
    else:
        if result["severity_level"] is not None:
            print("   ❌ severity_level must be null when bug_found is false")
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
# Ek tile ka pura cycle: VLM -> clean -> parse -> validate
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
# Tile results ko ek final report me merge karo
# Rule: koi bhi tile me bug -> page me bug
# -------------------------------------------------
def merge_results(tile_results):
    valid = [r for r in tile_results if r is not None]

    if not valid:
        return None

    bugs = [r for r in valid if r["bug_found"]]

    if not bugs:
        # Sabse kam confidence lo - conservative "no bug"
        lowest = min(valid, key=lambda r: r["confidence_score"])
        return {
            "bug_found": False,
            "description": "No visible UI bug was detected in this screenshot.",
            "severity_level": None,
            "confidence_score": lowest["confidence_score"],
            "fix": "No fix is required.",
        }

    # Sabse serious bug chuno; tie ho to highest confidence
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
# Main loop
# -------------------------------------------------
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