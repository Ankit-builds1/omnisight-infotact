from PIL import Image

img_path = "screenshots/broken/broken-button-clip/assets/broken-button-clip.png"
im = Image.open(img_path).convert("RGB")
width, height = im.size
pixels = im.load()

y_start = int(height * 0.15)
y_end = int(height * 0.55)
mid_y = (y_start + y_end) // 2  # scan along a single horizontal line through the button

def is_dark(x, y):
    r, g, b = pixels[x, y]
    return r < 100 and g < 100 and b < 100

# find first dark pixel from left
first_x = None
for x in range(0, width):
    if is_dark(x, mid_y):
        first_x = x
        break

# from first_x, walk right until we hit a long gap of non-dark pixels (end of first button)
last_x = first_x
gap = 0
GAP_LIMIT = 20  # pixels of continuous non-dark = button ended

for x in range(first_x, width):
    if is_dark(x, mid_y):
        last_x = x
        gap = 0
    else:
        gap += 1
        if gap > GAP_LIMIT:
            break

print(f"Image size: {width}x{height}")
print(f"First button spans x={first_x} to x={last_x}")
print(f"left fraction  = {first_x/width:.3f}")
print(f"right fraction = {last_x/width:.3f}")