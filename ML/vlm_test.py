import ollama


screenshots = [
    'ML/image_1.jpeg',
    'ML/image_2.jpeg',
    'ML/image_3.jpeg'
]

vlm_prompt = """
You are a strict QA engineer reviewing a UI screenshot.

FIRST, determine if there are any ACTUAL visual bugs (like cut-off text, overlapping elements, or broken layout).

- IF you find real visual bugs: List and describe them briefly.
- IF the screenshot looks clean, normal, or has NO clear bugs: Reply ONLY with "No visual issues detected." Do NOT invent or imagine any issues.
"""

for img_path in screenshots:
    print(f"\n================ Testing: {img_path} ================")
    try:
    
        with open(img_path, 'rb') as f:
            image_bytes = f.read()

        response = ollama.chat(
            model='llava',
            messages=[{
                'role': 'user',
                'content': vlm_prompt,
                'images': [image_bytes]  
            }]
        )
        
        print("\n[VLM Output]:\n", response['message']['content'])
        
    except Exception as e:
        print(f"Error testing {img_path}: {e}")