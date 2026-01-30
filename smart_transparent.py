#!/usr/bin/env python3
"""
Smart Background Removal with Fringe Cleanup

Algorithm:
1. Flood fill from image edges, stopping at dark pixels (outline)
2. Remove fringe pixels (bg-colored pixels adjacent to removed areas)
3. Result: clean transparent background with no color halo

For characters with interior regions matching background color (e.g., yellow hat
on yellow background), those regions may need manual restoration.
"""

from PIL import Image
import math
from collections import deque
import sys
from pathlib import Path


def color_dist(c1, c2):
    """Euclidean distance between two RGB colors."""
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(c1[:3], c2[:3])))


def is_dark(pixel, threshold=50):
    """Check if pixel is dark (part of outline)."""
    return pixel[0] < threshold and pixel[1] < threshold and pixel[2] < threshold


def detect_bg_color(pixels, w, h, sample_size=20):
    """Detect background color from image corners."""
    from collections import Counter
    corner_colors = []
    for x in range(sample_size):
        for y in range(sample_size):
            corner_colors.append(pixels[x, y][:3])
            corner_colors.append(pixels[w - 1 - x, y][:3])
            corner_colors.append(pixels[x, h - 1 - y][:3])
            corner_colors.append(pixels[w - 1 - x, h - 1 - y][:3])
    return Counter(corner_colors).most_common(1)[0][0]


def make_transparent(input_path, output_path=None, tolerance=10, fringe_tolerance=50):
    """
    Remove background with fringe cleanup.

    Args:
        input_path: Path to input image
        output_path: Path to save result (default: input_transparent.png)
        tolerance: Color matching tolerance for background detection
        fringe_tolerance: Higher tolerance for fringe pixel detection

    Returns:
        PIL Image with transparent background
    """
    img = Image.open(input_path).convert('RGBA')
    pixels = img.load()
    w, h = img.size

    # Detect background color
    bg_color = detect_bg_color(pixels, w, h)
    print(f"Detected background: RGB{bg_color}")

    def is_bg(pixel):
        return color_dist(pixel[:3], bg_color) < tolerance

    def is_fringe(pixel):
        return color_dist(pixel[:3], bg_color) < fringe_tolerance and not is_dark(pixel)

    # Step 1: Flood fill from edges, stopping at dark pixels
    visited = set()
    to_remove = set()
    queue = deque()

    for x in range(w):
        queue.append((x, 0))
        queue.append((x, h - 1))
    for y in range(h):
        queue.append((0, y))
        queue.append((w - 1, y))

    while queue:
        x, y = queue.popleft()

        if (x, y) in visited:
            continue
        if x < 0 or x >= w or y < 0 or y >= h:
            continue

        pixel = pixels[x, y]

        if is_dark(pixel):
            continue
        if not is_bg(pixel):
            continue

        visited.add((x, y))
        to_remove.add((x, y))
        queue.extend([(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)])

    print(f"Flood fill: {len(to_remove)} pixels")

    # Step 2: Fringe cleanup - remove bg-ish pixels adjacent to removed
    for pass_num in range(2):
        fringe = set()
        for (x, y) in to_remove:
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h:
                    if (nx, ny) not in to_remove:
                        pixel = pixels[nx, ny]
                        if is_fringe(pixel):
                            fringe.add((nx, ny))

        if not fringe:
            break

        to_remove.update(fringe)
        print(f"Fringe pass {pass_num + 1}: {len(fringe)} pixels")

    # Apply removal
    for (x, y) in to_remove:
        pixels[x, y] = (0, 0, 0, 0)

    # Save result
    if output_path is None:
        output_path = f"{Path(input_path).stem}_transparent.png"

    img.save(output_path, 'PNG')
    print(f"✓ Removed {len(to_remove)} pixels total")
    print(f"✓ Saved: {output_path}")

    return img


def apply_background(character_path, background_path, output_path=None, resample='nearest'):
    """
    Apply a new background to a character image.

    Args:
        character_path: Path to character image (should be transparent)
        background_path: Path to background image
        output_path: Where to save result
        resample: 'nearest' for pixel art, 'lanczos' for smooth scaling
    """
    char_img = Image.open(character_path).convert('RGBA')
    bg_img = Image.open(background_path).convert('RGBA')

    resample_method = Image.Resampling.NEAREST if resample == 'nearest' else Image.Resampling.LANCZOS
    char_scaled = char_img.resize(bg_img.size, resample_method)

    result = bg_img.copy()
    result.paste(char_scaled, (0, 0), char_scaled)

    if output_path is None:
        output_path = f"{Path(character_path).stem}_on_bg.png"

    result.save(output_path, 'PNG')
    print(f"✓ Saved: {output_path}")

    return result


def batch_process(input_dir, background_path, output_dir=None, tolerance=10):
    """
    Process all images in a directory.

    Args:
        input_dir: Directory with source images
        background_path: Background to apply
        output_dir: Output directory (default: input_dir_output)
        tolerance: Background detection tolerance
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir) if output_dir else Path(f"{input_dir}_output")
    output_path.mkdir(parents=True, exist_ok=True)

    image_extensions = {'.png', '.jpg', '.jpeg', '.webp'}

    processed = 0
    for img_file in sorted(input_path.iterdir()):
        if img_file.suffix.lower() not in image_extensions:
            continue

        try:
            # Make transparent
            temp_img = make_transparent(str(img_file), tolerance=tolerance)
            temp_path = f"/tmp/{img_file.stem}_temp.png"
            temp_img.save(temp_path, 'PNG')

            # Apply background
            output_file = output_path / f"{img_file.stem}.png"
            apply_background(temp_path, background_path, str(output_file))
            processed += 1
        except Exception as e:
            print(f"✗ Error processing {img_file.name}: {e}")

    print(f"\nProcessed {processed} images → {output_path}")


def main():
    if len(sys.argv) < 2:
        print("""
Smart Background Removal with Fringe Cleanup

Usage:
  Make transparent:
    python smart_transparent.py <image.png> [output.png]

  Apply background:
    python smart_transparent.py <character.png> --bg=<background.png> [output.png]

  Batch process:
    python smart_transparent.py --batch <input_dir> --bg=<background.png> [output_dir]

Options:
  --tolerance=N        Background detection tolerance (default: 10)
  --fringe-tolerance=N Fringe cleanup tolerance (default: 50)
  --bg=FILE            Apply this background image
  --batch              Process all images in directory
  --lanczos            Use LANCZOS resampling (default: NEAREST)

Examples:
  python smart_transparent.py pfp.png
  python smart_transparent.py pfp.png --bg=pattern.png output.png
  python smart_transparent.py --batch ./pfps --bg=bg.png ./output
        """)
        sys.exit(1)

    # Parse arguments
    input_file = None
    output_file = None
    bg_file = None
    tolerance = 10
    fringe_tolerance = 50
    resample = 'nearest'
    batch_mode = False

    args = sys.argv[1:]
    positional = []

    for arg in args:
        if arg.startswith('--tolerance='):
            tolerance = int(arg.split('=')[1])
        elif arg.startswith('--fringe-tolerance='):
            fringe_tolerance = int(arg.split('=')[1])
        elif arg.startswith('--bg='):
            bg_file = arg.split('=')[1]
        elif arg == '--lanczos':
            resample = 'lanczos'
        elif arg == '--batch':
            batch_mode = True
        elif not arg.startswith('--'):
            positional.append(arg)

    if batch_mode:
        if len(positional) < 1 or not bg_file:
            print("Batch mode requires: --batch <input_dir> --bg=<background.png>")
            sys.exit(1)
        input_dir = positional[0]
        output_dir = positional[1] if len(positional) > 1 else None
        batch_process(input_dir, bg_file, output_dir, tolerance)
    else:
        input_file = positional[0] if positional else None
        output_file = positional[1] if len(positional) > 1 else None

        if not input_file:
            print("Error: No input file specified")
            sys.exit(1)

        if bg_file:
            # Make transparent then apply background
            temp_img = make_transparent(input_file, tolerance=tolerance, fringe_tolerance=fringe_tolerance)
            temp_path = '/tmp/temp_transparent.png'
            temp_img.save(temp_path, 'PNG')

            if output_file is None:
                output_file = f"{Path(input_file).stem}_on_bg.png"

            apply_background(temp_path, bg_file, output_file, resample)
        else:
            # Just make transparent
            make_transparent(input_file, output_file, tolerance, fringe_tolerance)


if __name__ == '__main__':
    main()
