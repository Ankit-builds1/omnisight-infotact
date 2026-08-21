import os
import json
import re
import ollama

# -------------------------------------------------
# Test images
# -------------------------------------------------
image_paths = [
    "ML/images/broken-button-clip2.png",
    "screenshots/product-page.png",
    "screenshots/cart-page.png",
    "screenshots/confirmation-page.png"
]

# -------------------------------------------------
# Vision Audit Prompt
# -------------------------------------------------
prompt = """
Analyze this UI screenshot VERY CAREFULLY and identify if there is a REAL, VISIBLE UI bug.

CRITICAL RULES:
1. ONLY report a bug if you can ACTUALLY SEE it in THIS SPECIFIC screenshot.
2. DO NOT invent, assume, or imagine any UI elements not visibly present.
3. Pay special attention to:
   - Any button, image, or element that appears cut off at the right or left edge of the screen
   - Any element that seems too wide for its container or extends past the visible boundary
   - Text overlapping other text or elements
   - Text that is unreadable due to poor contrast

4. When in doubt, choose bug_found: false rather than inventing a bug.

5. IMPORTANT: You must ALWAYS include ALL 5 fields below in your JSON response, 
   even when bug_found is false. Never omit description or fix.
   - When bug_found is false: description = "No visible UI bugs detected in this screenshot.", fix = "No fix required."
   - When bug_found is true: describe the exact bug and exact fix.

Return ONLY valid JSON. Do NOT use markdown. Do NOT use ```json.

{
  "bug_found": true or false,
  "description": "description (never empty, see rule 5)",
  "fix": "fix (never empty, see rule 5)",
  "severity_level": "Critical, Major, Minor, or null",
  "confidence_score": number between 0.0 and 1.0
}

Rules:
1. bug_found must be true or false.
2. If bug_found is true, severity_level must be "Critical", "Major", or "Minor".
3. If bug_found is false, severity_level must be null.
4. confidence_score must be between 0.0 and 1.0.
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