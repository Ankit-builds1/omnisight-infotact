import os
import ollama

image_paths = [
    "ML/image_1.jpeg",
    "ML/image_2.jpeg",
    "ML/image_3.jpeg"
]

for img in image_paths:
    # 1. File Check
    if not os.path.exists(img):
        print(f"\n⚠️ Skipping {img}: File not found!")
        continue

    print(f"\n==================== Testing: {img} ====================")

    # 2. Crash-Proof Ollama API Call
    try:
        response = ollama.chat(
            model="llava",
            messages=[
                {
                    "role": "user",
                    "content": """
Analyze this screenshot for software/UI bugs.

You must return ONLY valid JSON and nothing else.

The JSON must contain exactly these three fields:

{
    "bug_found": true or false,
    "description": "description of the bug",
    "fix": "suggested fix"
}

Rules:
1. "bug_found" must be a boolean: true or false.
2. If a bug is found, set "bug_found" to true.
3. If a bug is found, describe the bug in "description".
4. If no bug is found, set "bug_found" to false.
5. If no bug is found, set "description" to "No bug detected."
6. If no bug is found, set "fix" to "No fix required."
7. Do not include any additional fields.
8. Do not include Markdown.
9. Do not write explanations outside the JSON.
10. Return only the JSON object.
""",
                    "images": [img],
                }
            ],
        )

        # 3. Safe Response Parsing
        if "message" in response and "content" in response["message"]:
            print(response["message"]["content"])
        else:
            print("❌ Error: Ollama se valid response text nahi mila.")

    except ollama.ResponseError as e:
        print(f"❌ Model Error: Model 'llava' load nahi ho paya. Details: {e.error}")
    except Exception as e:
        print(f"❌ Connection Error: Kya Ollama application backend par chal raha hai? Details: {e}")