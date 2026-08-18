import os
import json
import ollama

image_paths = ["image_1.jpeg", "image_2.jpeg", "image_3.jpeg"]

for img in image_paths:
    if not os.path.exists(img):
        print(f"\n⚠️ Skipping {img}: File not found!")
        continue

    print(f"\n==================== Testing: {img} ====================")

    try:
        response = ollama.chat(
            model="llava",
            options={"temperature": 0.1}, # <-- IMPORTANT: Consistency ke liye
            messages=[
                {
                    "role": "user",
                    "content": f"""
You are a QA tester. Analyze this screenshot for UI/UX bugs.

CRITICAL RULE: Look specifically for these bugs:
1. Text cut off or overlapping inside input fields, buttons
2. Misaligned elements
3. Broken layouts
4. Poor contrast making text unreadable

Return ONLY valid JSON. No markdown.

JSON Format:
{{
    "bug_found": true or false,
    "description": "description of the bug",
    "fix": "suggested fix",
    "confidence_score": 0.0 to 1.0,
    "severity_level": null | "Minor" | "Major" | "Critical"
}}

EXAMPLE 1 - Bug Found:
{{
    "bug_found": true,
    "description": "Text inside input fields is partially obscured and not fully visible",
    "fix": "Increase padding and height of input fields in CSS",
    "confidence_score": 0.85,
    "severity_level": "Major"
}}

EXAMPLE 2 - No Bug:
{{
    "bug_found": false,
    "description": "No bug detected.",
    "fix": "No fix required.",
    "confidence_score": 0.95,
    "severity_level": null
}}

Rules:
1. If bug_found is false, severity_level MUST be null
2. If bug_found is true, severity_level MUST be "Minor", "Major", or "Critical"
3. Be honest. If you see overlapping text, it's a bug.
""",
                    "images": [img],
                }
            ],
        )

        if "message" in response and "content" in response["message"]:
            result_str = response["message"]["content"].strip()
            result_str = result_str.replace("```json", "").replace("```", "")

            try:
                result = json.loads(result_str.strip())
                if result.get("bug_found") is False:
                    result["severity_level"] = None
                print(json.dumps(result, indent=4))
            except json.JSONDecodeError:
                print("❌ Error: Invalid JSON")
                print(result_str)
        else:
            print("❌ Error: No response from Ollama.")

    except Exception as e:
        print(f"❌ Error: {e}")