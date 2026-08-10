import ollama

IMAGE_PATH = "ML/test_image.jpg"

response = ollama.chat(
    model="llava",
    messages=[
        {
            "role": "user",
            "content": "Describe this image in detail.",
            "images": [IMAGE_PATH],
        }
    ],
)

print("\nLLaVA Response:\n")
print(response["message"]["content"])