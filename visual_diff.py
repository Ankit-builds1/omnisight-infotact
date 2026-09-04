#!/usr/bin/env python3
"""
visual_diff.py - compares a before/after screenshot pair and produces a highlighted diff image,
so a PR (or a VLM) can see exactly which regions of a page actually changed.

Usage:
    python visual_diff.py <before.png> <after.png> <output-diff.png>

What it does:
    - loads both images (resizes 'after' to match 'before' if the sizes don't line up)
    - computes a per-pixel difference and thresholds it into a changed/unchanged mask
    - paints every changed pixel semi-transparent red directly over the 'after' screenshot
    - draws a bounding box around the overall changed region so it's obvious at a glance
    - prints a quick summary: bounding box + how many pixels changed
"""
import sys
from PIL import Image, ImageChops, ImageDraw

THRESHOLD = 30                        # how different a pixel needs to be (0-255 per channel) to count as "changed"
HIGHLIGHT_COLOR = (255, 0, 0, 120)    # semi-transparent red overlay on changed pixels
BOX_COLOR = (255, 0, 0, 255)          # solid red for the bounding box outline


def load_and_align(before_path, after_path):
    before = Image.open(before_path).convert('RGB')
    after = Image.open(after_path).convert('RGB')

    if before.size != after.size:
        print(f"warning: size mismatch {before.size} vs {after.size} - resizing 'after' to match 'before'")
        after = after.resize(before.size)

    return before, after


def compute_diff_mask(before, after):
    diff = ImageChops.difference(before, after)
    gray = diff.convert('L')  # collapse rgb diff down to a single "how different" value per pixel
    mask = gray.point(lambda p: 255 if p > THRESHOLD else 0)
    return mask


def highlight_diff(after, mask, output_path):
    bbox = mask.getbbox()
    if bbox is None:
        print("no differences found above threshold - images are effectively identical")
        after.save(output_path)
        return

    overlay = Image.new('RGBA', after.size, (0, 0, 0, 0))
    overlay.paste(Image.new('RGBA', after.size, HIGHLIGHT_COLOR), (0, 0), mask)

    draw = ImageDraw.Draw(overlay)
    draw.rectangle(bbox, outline=BOX_COLOR, width=3)

    result = Image.alpha_composite(after.convert('RGBA'), overlay)
    result.convert('RGB').save(output_path)

    changed_pixels = mask.histogram()[255]  # count of pixels with value 255 (i.e. "changed")
    total_pixels = mask.width * mask.height
    pct = (changed_pixels / total_pixels) * 100

    print(f"diff saved to {output_path}")
    print(f"changed region bounding box: {bbox}")
    print(f"{changed_pixels} pixels changed ({pct:.2f}% of image)")


def main():
    if len(sys.argv) != 4:
        print("usage: python visual_diff.py <before.png> <after.png> <output-diff.png>")
        sys.exit(1)

    before_path, after_path, output_path = sys.argv[1:4]
    before, after = load_and_align(before_path, after_path)
    mask = compute_diff_mask(before, after)
    highlight_diff(after, mask, output_path)


if __name__ == '__main__':
    main()
