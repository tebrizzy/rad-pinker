#!/usr/bin/env python3
"""
Background Replacer Tool
- For images with solid backgrounds: detect and replace with new background
- For images with transparent backgrounds: just composite onto new background
Uses flood fill from edges to preserve elements inside the character.
"""

import sys
import math
from PIL import Image
from pathlib import Path
from collections import deque, Counter

TOLERANCE = 35  # Color distance tolerance

def color_distance(c1, c2):
    """Calculate Euclidean distance between two RGB colors."""
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(c1[:3], c2[:3])))

def is_target_color(pixel, target, tolerance=TOLERANCE):
    """Check if a pixel matches the target color within tolerance."""
    if len(pixel) == 4 and pixel[3] == 0:  # Already transparent
        return False
    return color_distance(pixel[:3], target[:3]) < tolerance

def has_transparent_background(img):
    """
    Check if image already has a transparent background.
    Returns True if most edge pixels are transparent.
    """
    pixels = img.load()
    width, height = img.size
    transparent_count = 0
    total_edge = 0

    # Check edge pixels for transparency
    for x in range(width):
        if pixels[x, 0][3] == 0:  # Top edge
            transparent_count += 1
        if pixels[x, height - 1][3] == 0:  # Bottom edge
            transparent_count += 1
        total_edge += 2
    for y in range(height):
        if pixels[0, y][3] == 0:  # Left edge
            transparent_count += 1
        if pixels[width - 1, y][3] == 0:  # Right edge
            transparent_count += 1
        total_edge += 2

    # If more than 50% of edges are transparent, it's already transparent
    return transparent_count / total_edge > 0.5

def detect_background_color(img):
    """
    Detect background color by sampling edge pixels.
    Returns the most common non-transparent color found on edges.
    """
    pixels = img.load()
    width, height = img.size
    edge_colors = []

    # Sample all edge pixels (only opaque ones)
    for x in range(width):
        if pixels[x, 0][3] > 0:
            edge_colors.append(pixels[x, 0][:3])
        if pixels[x, height - 1][3] > 0:
            edge_colors.append(pixels[x, height - 1][:3])
    for y in range(height):
        if pixels[0, y][3] > 0:
            edge_colors.append(pixels[0, y][:3])
        if pixels[width - 1, y][3] > 0:
            edge_colors.append(pixels[width - 1, y][:3])

    if not edge_colors:
        return None

    # Find most common color
    color_counts = Counter(edge_colors)
    bg_color = color_counts.most_common(1)[0][0]
    return bg_color

def flood_fill_background(img, bg_color):
    """
    Flood fill from edges to find background pixels.
    Returns a set of (x, y) coordinates that are background.
    """
    pixels = img.load()
    width, height = img.size
    visited = set()
    background = set()
    queue = deque()

    # Start from all edge pixels that match background color
    for x in range(width):
        if is_target_color(pixels[x, 0], bg_color):
            queue.append((x, 0))
        if is_target_color(pixels[x, height - 1], bg_color):
            queue.append((x, height - 1))
    for y in range(height):
        if is_target_color(pixels[0, y], bg_color):
            queue.append((0, y))
        if is_target_color(pixels[width - 1, y], bg_color):
            queue.append((width - 1, y))

    # Flood fill
    while queue:
        x, y = queue.popleft()
        if (x, y) in visited:
            continue
        if x < 0 or x >= width or y < 0 or y >= height:
            continue

        pixel = pixels[x, y]
        if not is_target_color(pixel, bg_color):
            continue

        visited.add((x, y))
        background.add((x, y))

        # Add neighbors (4-connected)
        queue.append((x + 1, y))
        queue.append((x - 1, y))
        queue.append((x, y + 1))
        queue.append((x, y - 1))

    return background

def replace_background(input_path, background_path, output_path):
    """Replace background with new background image."""
    # Load images
    img = Image.open(input_path).convert('RGBA')
    background = Image.open(background_path).convert('RGBA')

    # Resize background to match input image size
    background = background.resize(img.size, Image.Resampling.NEAREST)

    # Check if image already has transparent background
    if has_transparent_background(img):
        # Just composite - no color replacement needed
        final = Image.alpha_composite(background, img)
        final.save(output_path, 'PNG')
        print(f"✓ Saved: {output_path} (transparent bg - composited only)")
        return

    # Auto-detect background color
    bg_color = detect_background_color(img)
    if bg_color is None:
        # Fallback - just composite
        final = Image.alpha_composite(background, img)
        final.save(output_path, 'PNG')
        print(f"✓ Saved: {output_path} (no bg detected - composited only)")
        return

    # Find background pixels using flood fill
    bg_pixels = flood_fill_background(img, bg_color)

    # Get pixel data
    pixels = img.load()

    # Replace only background pixels with transparent
    for (x, y) in bg_pixels:
        pixels[x, y] = (0, 0, 0, 0)

    # Composite: background + character
    final = Image.alpha_composite(background, img)

    # Save
    final.save(output_path, 'PNG')
    print(f"✓ Saved: {output_path} (detected bg: rgb{bg_color})")

def batch_replace(input_folder, background_path, output_folder):
    """Process all images in a folder."""
    input_path = Path(input_folder)
    output_path = Path(output_folder)
    output_path.mkdir(parents=True, exist_ok=True)

    image_extensions = {'.png', '.jpg', '.jpeg', '.webp'}
    bg_name = Path(background_path).name

    processed = 0
    for img_file in sorted(input_path.iterdir()):
        if img_file.suffix.lower() in image_extensions:
            if img_file.name == bg_name:
                continue
            output_file = output_path / f"{img_file.stem}_pink.png"
            try:
                replace_background(str(img_file), background_path, str(output_file))
                processed += 1
            except Exception as e:
                print(f"✗ Error processing {img_file.name}: {e}")

    print(f"\nProcessed {processed} images → {output_folder}")

def main():
    if len(sys.argv) < 3:
        print("""
Background Replacer - Auto-detect and replace backgrounds

Usage:
  Single file:  python replace_background.py <input.png> <background.png> [output.png]
  Batch folder: python replace_background.py --batch <input_folder> <background.png> [output_folder]

Examples:
  python replace_background.py wizard.png pink_pattern.png wizard_pink.png
  python replace_background.py --batch ./rads pink_pattern.png ./rads_pink
        """)
        sys.exit(1)

    if sys.argv[1] == '--batch':
        input_folder = sys.argv[2]
        background = sys.argv[3]
        output_folder = sys.argv[4] if len(sys.argv) > 4 else f"{input_folder}_output"
        batch_replace(input_folder, background, output_folder)
    else:
        input_file = sys.argv[1]
        background = sys.argv[2]
        output_file = sys.argv[3] if len(sys.argv) > 3 else f"{Path(input_file).stem}_pink.png"
        replace_background(input_file, background, output_file)

if __name__ == '__main__':
    main()
