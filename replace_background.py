#!/usr/bin/env python3
"""
Background Replacer Tool
- For images with solid backgrounds: detect and replace with new background
- For images with transparent backgrounds: just composite onto new background
Uses flood fill from edges + fringe removal for clean edges.
"""

import sys
import math
import colorsys
from PIL import Image
from pathlib import Path
from collections import deque, Counter

TOLERANCE = 45  # Color distance tolerance for flood fill
FRINGE_TOLERANCE = 55  # Moderate tolerance for fringe cleanup
HUE_TOLERANCE = 0.12  # Hue similarity threshold (0-1 scale)

def color_distance(c1, c2):
    """Calculate Euclidean distance between two RGB colors."""
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(c1[:3], c2[:3])))

def rgb_to_hue(rgb):
    """Convert RGB to hue (0-1 scale). Returns None for grayscale."""
    r, g, b = rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    if s < 0.1:  # Too desaturated to have meaningful hue
        return None
    return h

def hue_distance(h1, h2):
    """Calculate circular distance between two hues (0-1 scale)."""
    if h1 is None or h2 is None:
        return 1.0  # Max distance if either is grayscale
    diff = abs(h1 - h2)
    return min(diff, 1.0 - diff)

def is_target_color(pixel, target, tolerance=TOLERANCE):
    """Check if a pixel matches the target color within tolerance."""
    if len(pixel) == 4 and pixel[3] == 0:  # Already transparent
        return False
    return color_distance(pixel[:3], target[:3]) < tolerance

def is_fringe_pixel(pixel, bg_color, bg_hue):
    """
    Check if pixel is a fringe/edge pixel contaminated by background color.
    Balanced approach - close color match OR (similar hue AND saturated).
    """
    if len(pixel) == 4 and pixel[3] == 0:
        return False

    dist = color_distance(pixel[:3], bg_color[:3])

    # Very close to bg color - definitely fringe
    if dist < 40:
        return True

    # Moderately close + similar hue = likely fringe
    if dist < FRINGE_TOLERANCE:
        pixel_hue = rgb_to_hue(pixel[:3])
        if pixel_hue is not None and bg_hue is not None:
            if hue_distance(pixel_hue, bg_hue) < HUE_TOLERANCE:
                # Check saturation - only remove if noticeably colored
                r, g, b = pixel[0] / 255.0, pixel[1] / 255.0, pixel[2] / 255.0
                _, l, s = colorsys.rgb_to_hls(r, g, b)
                # Don't remove dark pixels (likely intentional dark outlines)
                if s > 0.25 and l > 0.2:
                    return True

    return False

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

def remove_fringe(img, background_pixels, bg_color):
    """
    Remove fringe pixels adjacent to background that have background color contamination.
    Does multiple passes to clean up anti-aliased edges.
    """
    pixels = img.load()
    width, height = img.size
    bg_hue = rgb_to_hue(bg_color)

    removed = set(background_pixels)

    # Single pass for pixel art (hard edges, not anti-aliased)
    for _ in range(1):
        fringe = set()

        # Find pixels adjacent to removed pixels
        for (x, y) in removed:
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < width and 0 <= ny < height:
                    if (nx, ny) not in removed:
                        pixel = pixels[nx, ny]
                        if is_fringe_pixel(pixel, bg_color, bg_hue):
                            fringe.add((nx, ny))

        if not fringe:
            break

        removed.update(fringe)

    return removed

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

    # Remove fringe pixels (anti-aliased edges with background color bleed)
    all_removed = remove_fringe(img, bg_pixels, bg_color)

    # Get pixel data
    pixels = img.load()

    # Replace background + fringe pixels with transparent
    for (x, y) in all_removed:
        pixels[x, y] = (0, 0, 0, 0)

    # Composite: background + character
    final = Image.alpha_composite(background, img)

    # Save
    final.save(output_path, 'PNG')
    fringe_count = len(all_removed) - len(bg_pixels)
    print(f"✓ Saved: {output_path} (bg: rgb{bg_color}, removed {len(bg_pixels)} bg + {fringe_count} fringe pixels)")

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
