import os
import ollama


image_paths = [
    "ML/image_1.jpeg",
    "ML/image_2.jpeg",  
    "ML/image_3.jpeg"
]

for img in image_paths:
    if not os.path.exists(img):
        print(f"\nSkipping {img}: File not found!")
        continue

    print(f"\n==================== Testing: {img} ====================")
    response = ollama.chat(
        model="llava",
        messages=[
            {
                "role": "user",
                "content": "Describe this image in detail.",
                "images": [img],
            }
        ],
    )
    print(response["message"]["content"])