from PIL import Image

img_path = "screenshots/broken/broken-button-clip/assets/broken-button-clip.png"
im = Image.open(img_path).convert("RGB")
width, height = im.size
pixels = im.load()

# Search only within the top product-card band (top=0.15 to bottom=0.55 of height)
y_start = int(height * 0.15)
y_end = int(height * 0.55)

min_x = width
max_x = 0

for y in range(y_start, y_end):
    for x in range(0, width):
        r, g, b = pixels[x, y]
        # button color is dark (teal/near-black) — not white background
        if r < 100 and g < 100 and b < 100:
            if x < min_x:
                min_x = x
            if x > max_x:
                max_x = x

print(f"Image size: {width}x{height}")
print(f"Dark button pixels found from x={min_x} to x={max_x}")
print(f"left fraction  = {min_x/width:.3f}")
print(f"right fraction = {max_x/width:.3f}")