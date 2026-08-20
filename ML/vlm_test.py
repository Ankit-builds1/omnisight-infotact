import os
import json
import re
import ollama

# -------------------------------------------------
# Test images
# -------------------------------------------------
image_paths = [
    "ML/images/broken-button-clip.png",
    "screenshots/product-page.png",
    "screenshots/cart-page.png",
    "screenshots/confirmation-page.png"
]

# -------------------------------------------------
# Vision Audit Prompt
# -------------------------------------------------

prompt = """
Analyze this UI screenshot and determine whether there is a visible UI bug.

Perform a careful visual inspection of the screenshot.

Check specifically for:
- incorrect button labels
- spelling mistakes
- capitalization problems
- incorrect or inconsistent text
- alignment problems
- spacing problems
- overlapping elements
- missing UI elements
- broken UI elements
- inconsistent fonts or styles
- incorrect visual states
- obvious layout problems

A bug may be subtle. Pay close attention to small text and UI labels.

Only report a bug when there is visible evidence in the screenshot.
Do not invent or assume bugs.

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
   - severity_level must be exactly one of:
     "Critical", "Major", "Minor"
   - confidence_score must be a decimal between 0.0 and 1.0.
   - fix must explain how to correct the bug.

3. If bug_found is false:
   - description must say that no visible UI bug was detected.
   - severity_level must be null.
   - confidence_score must be a decimal between 0.0 and 1.0.
   - fix must say that no fix is required.

4. Never use confidence values such as 90 or 95.
   Use values such as 0.90 or 0.95.

5. Base the result only on visible evidence in the screenshot.

6. Return ONLY the JSON object.
"""


# -------------------------------------------------
# Test each screenshot
# -------------------------------------------------

for img in image_paths:

    if not os.path.exists(img):
        print(f"\n⚠️ Skipping {img}: File not found!")
        continue

    print(f"\n==================== Testing: {img} ====================")

    try:

        # -----------------------------------------
        # Send image to LLaVA
        # -----------------------------------------

        response = ollama.chat(
            model="llava",
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                    "images": [img]
                }
            ]
        )

        # -----------------------------------------
        # Get raw model output
        # -----------------------------------------

        raw_output = response["message"]["content"]

        print("\nRaw model output:")
        print(raw_output)

        # -----------------------------------------
        # Clean Markdown code fences
        # -----------------------------------------

        clean_output = raw_output.strip()

        clean_output = re.sub(
            r"^```(?:json)?\s*",
            "",
            clean_output,
            flags=re.IGNORECASE
        )

        clean_output = re.sub(
            r"\s*```$",
            "",
            clean_output
        ).strip()

        # -----------------------------------------
        # Parse JSON
        # -----------------------------------------

        try:

            result = json.loads(clean_output)

            # -----------------------------------------
            # Required fields
            # -----------------------------------------

            required_fields = [
                "bug_found",
                "description",
                "severity_level",
                "confidence_score",
                "fix"
            ]

            missing_fields = [
                field
                for field in required_fields
                if field not in result
            ]

            if missing_fields:
                print("\n❌ Missing fields:", missing_fields)
                continue

            # -----------------------------------------
            # Check for unexpected fields
            # -----------------------------------------

            extra_fields = (
                set(result.keys()) - set(required_fields)
            )

            if extra_fields:
                print("\n❌ Unexpected fields:", extra_fields)
                continue

            # -----------------------------------------
            # Validate bug_found
            # -----------------------------------------

            if not isinstance(result["bug_found"], bool):
                print("\n❌ bug_found must be true or false")
                continue

            # -----------------------------------------
            # Validate description
            # -----------------------------------------

            if not isinstance(result["description"], str):
                print("\n❌ description must be a string")
                continue

            # -----------------------------------------
            # Validate fix
            # -----------------------------------------

            if not isinstance(result["fix"], str):
                print("\n❌ fix must be a string")
                continue

            # -----------------------------------------
            # Validate severity_level
            # -----------------------------------------

            if result["bug_found"]:

                if result["severity_level"] not in [
                    "Critical",
                    "Major",
                    "Minor"
                ]:
                    print("\n❌ Invalid severity_level")
                    print(
                        "Expected: Critical, Major, or Minor"
                    )
                    continue

            else:

                if result["severity_level"] is not None:
                    print(
                        "\n❌ severity_level must be null "
                        "when bug_found is false"
                    )
                    continue

            # -----------------------------------------
            # Validate confidence_score
            # -----------------------------------------

            try:

                result["confidence_score"] = float(
                    result["confidence_score"]
                )

            except (ValueError, TypeError):

                print("\n❌ Invalid confidence_score")
                continue

            if not 0.0 <= result["confidence_score"] <= 1.0:

                print(
                    "\n❌ confidence_score must be "
                    "between 0.0 and 1.0"
                )
                continue

            # -----------------------------------------
            # Final valid result
            # -----------------------------------------

            print("\n✅ Valid JSON:")
            print(json.dumps(result, indent=2))

            # -----------------------------------------
            # Vision Audit Result
            # -----------------------------------------

            if result["bug_found"]:

                print("\n🔴 BUG DETECTED")

            else:

                print("\n🟢 NO BUG DETECTED")

        except json.JSONDecodeError as e:

            print("\n❌ Model did not return valid JSON")
            print("JSON Error:", e)

            print("\nCleaned output:")
            print(clean_output)

    except Exception as e:

        print(f"\n❌ Error: {e}")