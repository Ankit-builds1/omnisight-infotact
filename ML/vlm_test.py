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
                    "content": "Describe this image in detail.",
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