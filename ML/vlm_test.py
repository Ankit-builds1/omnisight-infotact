import os
import json
import re
import ollama

image_paths = [
    "ML/images/broken-button-clip.png"
]

for img in image_paths:

    if not os.path.exists(img):
        print(f"\n⚠️ Skipping {img}: File not found!")
        continue

    print(f"\n==================== Testing: {img} ====================")

    try:
        response = ollama.chat(
            model="llava",
            messages=[
                {
                    "role": "user",
                    "content": """
Analyze this UI screenshot and identify whether there is a visible UI bug.

Return ONLY valid JSON.
Do NOT use markdown.
Do NOT use ```json.
Do NOT add any explanation outside the JSON.

The JSON must have exactly these fields:

{
  "bug_found": true or false,
  "description": "short description of the bug",
  "fix": "recommended fix",
  "severity_level": "Critical, Major, Minor, or null",
  "confidence_score": number between 0.0 and 1.0
}

Rules:

1. bug_found must be either true or false.

2. If bug_found is true:
   - severity_level must be exactly one of:
     "Critical", "Major", "Minor"

3. If bug_found is false:
   - severity_level must be null.

4. confidence_score must be a decimal number between 0.0 and 1.0.
   Example: 0.85

5. Return ONLY the JSON object.
""",
                    "images": [img]
                }
            ]
        )

        raw_output = response["message"]["content"]

        print("\nRaw model output:")
        print(raw_output)

        # -----------------------------------------
        # Clean Markdown code fences
        # -----------------------------------------

        clean_output = raw_output.strip()

        if clean_output.startswith("```"):
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
                "fix",
                "severity_level",
                "confidence_score"
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

        except json.JSONDecodeError as e:

            print("\n❌ Model did not return valid JSON")
            print("JSON Error:", e)

            print("\nCleaned output:")
            print(clean_output)

    except Exception as e:
        print(f"\n❌ Error: {e}")