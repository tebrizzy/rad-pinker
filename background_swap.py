#!/usr/bin/env python3
"""
Background Swap Script
Replaces a solid color background with a tiled pattern background
while preserving the character/subject artwork.

Supports:
- Auto-detection of background color from corners
- Multi-pass cleanup for anti-aliased edges
- Tiled background generation from source image
- Generic color-based replacement (not just teal)
"""

from PIL import Image
import numpy as np
import sys
from pathlib import Path


def create_tiled_background(source_img_path, target_size, tile_size=40):
    """
    Create a tiled background from a corner of the source image.
    Uses corner to avoid any logos/designs in the center.
    """
    source = Image.open(source_img_path)
    source_arr = np.array(source)

    # Extract tile from top-left corner (away from any central design)
    tile = source_arr[:tile_size, :tile_size]

    h, w = target_size
    channels = tile.shape[2] if len(tile.shape) > 2 else 3
    tiled_bg = np.zeros((h, w, channels), dtype=np.uint8)

    for y in range(0, h, tile_size):
        for x in range(0, w, tile_size):
            y_end = min(y + tile_size, h)
            x_end = min(x + tile_size, w)
            tile_h = y_end - y
            tile_w = x_end - x
            tiled_bg[y:y_end, x:x_end] = tile[:tile_h, :tile_w]

    return tiled_bg


def detect_background_color(img_arr, sample_size=20):
    """Detect dominant background color from image corners."""
    h, w = img_arr.shape[:2]

    # Sample from all four corners
    corners = [
        img_arr[:sample_size, :sample_size],           # top-left
        img_arr[:sample_size, -sample_size:],          # top-right
        img_arr[-sample_size:, :sample_size],          # bottom-left
        img_arr[-sample_size:, -sample_size:],         # bottom-right
    ]

    all_samples = np.concatenate([c.reshape(-1, 3) for c in corners])
    bg_color = np.median(all_samples, axis=0).astype(int)

    return tuple(bg_color)


def color_distance(c1, c2):
    """Euclidean distance between two RGB colors."""
    return np.sqrt(sum((a - b) ** 2 for a, b in zip(c1, c2)))


def is_background_pixel(pixel, bg_color, tolerance=45):
    """Check if pixel matches background color within tolerance."""
    return color_distance(pixel[:3], bg_color) < tolerance


def swap_background_generic(character_img_path, background_source_path, output_path,
                           tile_size=40, tolerance=45, use_tiling=True):
    """
    Replace the background of a character image.

    Args:
        character_img_path: Path to character/PFP image
        background_source_path: Path to background image
        output_path: Where to save result
        tile_size: Size of tiles if using tiling mode
        tolerance: Color matching tolerance (higher = more aggressive)
        use_tiling: If True, tile the background; if False, resize it
    """
    # Load character image
    character_img = Image.open(character_img_path).convert('RGB')
    character_arr = np.array(character_img)
    h, w = character_arr.shape[:2]

    # Create/load background
    if use_tiling:
        new_bg = create_tiled_background(background_source_path, (h, w), tile_size)
    else:
        bg_img = Image.open(background_source_path).convert('RGB')
        bg_img = bg_img.resize((w, h), Image.Resampling.LANCZOS)
        new_bg = np.array(bg_img)

    # Detect background color
    bg_color = detect_background_color(character_arr)
    print(f"Detected background color: RGB{bg_color}")

    result = character_arr.copy()

    # Multi-pass replacement with increasing tolerance
    passes = [
        (tolerance, "pure background"),
        (tolerance + 15, "edge artifacts"),
        (tolerance + 30, "remaining artifacts"),
    ]

    for pass_tolerance, desc in passes:
        replaced = 0
        for y in range(h):
            for x in range(w):
                pixel = result[y, x]
                if is_background_pixel(pixel, bg_color, pass_tolerance):
                    result[y, x] = new_bg[y, x]
                    replaced += 1
        print(f"Pass ({desc}): replaced {replaced} pixels")

    # Save result
    result_img = Image.fromarray(result)
    result_img.save(output_path)
    print(f"✓ Saved: {output_path}")

    return result


def swap_background_teal(character_img_path, background_source_path, output_path, tile_size=40):
    """
    Original teal-specific background swap with multi-pass cleanup.
    Optimized for teal/cyan backgrounds (~RGB 25, 240, 180).
    """
    character_img = Image.open(character_img_path)
    character_arr = np.array(character_img)
    h, w = character_arr.shape[:2]

    # Create the tiled background
    tiled_bg = create_tiled_background(background_source_path, (h, w), tile_size)

    # Detect background color
    corner_sample = character_arr[:20, :20]
    bg_color = np.median(corner_sample.reshape(-1, 3), axis=0)
    print(f"Detected background color: RGB{tuple(bg_color.astype(int))}")

    result = character_arr.copy()

    # --- PASS 1: Replace pure/bright background ---
    for y in range(h):
        for x in range(w):
            r, g, b = int(result[y, x, 0]), int(result[y, x, 1]), int(result[y, x, 2])
            if g > 200 and b > 150 and r < 80:
                result[y, x] = tiled_bg[y, x]
    print("Pass 1: Replaced pure background pixels")

    # --- PASS 2: Clean up medium-bright teal artifacts ---
    for y in range(h):
        for x in range(w):
            r, g, b = int(result[y, x, 0]), int(result[y, x, 1]), int(result[y, x, 2])
            if g > 140 and b > 100 and r < 100 and g > r and g > b:
                result[y, x] = tiled_bg[y, x]
    print("Pass 2: Cleaned medium-bright edge artifacts")

    # --- PASS 3: Clean up darker teal artifacts ---
    for y in range(h):
        for x in range(w):
            r, g, b = int(result[y, x, 0]), int(result[y, x, 1]), int(result[y, x, 2])
            if g > 120 and r < 100 and g > r and g > b - 20:
                result[y, x] = tiled_bg[y, x]
    print("Pass 3: Cleaned darker teal artifacts")

    # --- PASS 4: Clean up remaining artifacts ---
    for y in range(h):
        for x in range(w):
            r, g, b = int(result[y, x, 0]), int(result[y, x, 1]), int(result[y, x, 2])
            if g > 100 and r < 80 and g > r + 20:
                result[y, x] = tiled_bg[y, x]
    print("Pass 4: Cleaned remaining artifacts")

    # --- PASS 5: Final cleanup ---
    for y in range(h):
        for x in range(w):
            r, g, b = int(result[y, x, 0]), int(result[y, x, 1]), int(result[y, x, 2])
            brightness = (r + g + b) / 3
            if g > r + 10 and g > 40 and brightness >= 30:
                result[y, x] = tiled_bg[y, x]
    print("Pass 5: Final cleanup (preserving very dark outlines)")

    # Save result
    result_img = Image.fromarray(result)
    result_img.save(output_path)
    print(f"✓ Saved: {output_path}")

    return result


def main():
    if len(sys.argv) < 3:
        print("""
Background Swap - Replace backgrounds with tiled or scaled patterns

Usage:
  python background_swap.py <character.png> <background.png> [output.png] [options]

Options:
  --teal       Use teal-optimized multi-pass (for cyan/teal backgrounds)
  --tile=N     Tile size in pixels (default: 40)
  --no-tile    Resize background instead of tiling
  --tolerance=N Color matching tolerance (default: 45)

Examples:
  python background_swap.py wizard.png pattern.png wizard_new.png
  python background_swap.py nft.png pink.png nft_pink.png --teal
  python background_swap.py char.png bg.png out.png --no-tile --tolerance=60
        """)
        sys.exit(1)

    character_path = sys.argv[1]
    background_path = sys.argv[2]
    output_path = sys.argv[3] if len(sys.argv) > 3 and not sys.argv[3].startswith('--') else f"{Path(character_path).stem}_swapped.png"

    # Parse options
    use_teal = '--teal' in sys.argv
    use_tiling = '--no-tile' not in sys.argv
    tile_size = 40
    tolerance = 45

    for arg in sys.argv:
        if arg.startswith('--tile='):
            tile_size = int(arg.split('=')[1])
        if arg.startswith('--tolerance='):
            tolerance = int(arg.split('=')[1])

    if use_teal:
        swap_background_teal(character_path, background_path, output_path, tile_size)
    else:
        swap_background_generic(character_path, background_path, output_path,
                               tile_size, tolerance, use_tiling)


if __name__ == '__main__':
    main()
