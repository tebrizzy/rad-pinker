#!/usr/bin/env python3
"""
Remove leftover colored dots from images.
Removes small isolated clusters of specified colors.
"""

import sys
import math
from PIL import Image
from pathlib import Path
from collections import deque

# Colors to clean up
COLORS_TO_REMOVE = [
    ((252, 225, 132), 50),  # Yellow
    ((255, 249, 225), 50),  # Cream
    ((62, 130, 255), 50),   # Blue
    ((21, 241, 179), 50),   # Teal/Green
]

TOLERANCE = 45

def color_distance(c1, c2):
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(c1[:3], c2[:3])))

def matches_any_target(pixel):
    """Check if pixel matches any of the target colors to remove."""
    if len(pixel) == 4 and pixel[3] == 0:
        return False
    for target, _ in COLORS_TO_REMOVE:
        if color_distance(pixel[:3], target) < TOLERANCE:
            return True
    return False

def find_colored_clusters(img):
    """Find all clusters of target-colored pixels."""
    pixels = img.load()
    width, height = img.size
    visited = set()
    clusters = []

    for y in range(height):
        for x in range(width):
            if (x, y) in visited:
                continue
            if not matches_any_target(pixels[x, y]):
                continue

            # BFS to find cluster
            cluster = set()
            queue = deque([(x, y)])
            while queue:
                cx, cy = queue.popleft()
                if (cx, cy) in visited:
                    continue
                if cx < 0 or cx >= width or cy < 0 or cy >= height:
                    continue
                if not matches_any_target(pixels[cx, cy]):
                    continue

                visited.add((cx, cy))
                cluster.add((cx, cy))
                queue.append((cx + 1, cy))
                queue.append((cx - 1, cy))
                queue.append((cx, cy + 1))
                queue.append((cx, cy - 1))

            if cluster:
                clusters.append(cluster)

    return clusters

def cleanup_image(input_path, bg_path, max_cluster_size=30):
    """Remove small colored clusters from image."""
    img = Image.open(input_path).convert('RGBA')
    pixels = img.load()

    clusters = find_colored_clusters(img)
    removed = 0

    for cluster in clusters:
        if len(cluster) <= max_cluster_size:
            for (x, y) in cluster:
                pixels[x, y] = (0, 0, 0, 0)
            removed += len(cluster)

    # Composite with background
    background = Image.open(bg_path).convert('RGBA')
    background = background.resize(img.size, Image.Resampling.NEAREST)
    final = Image.alpha_composite(background, img)
    final.save(input_path, 'PNG')

    return removed

def main():
    bg_path = "/Users/zen/Desktop/solanamobi/radshader-hd-2026-01-29T12-24-24.png"

    files_to_fix = sys.argv[1:] if len(sys.argv) > 1 else []

    if not files_to_fix:
        print("Usage: python cleanup_dots.py <file1.png> [file2.png] ...")
        sys.exit(1)

    for f in files_to_fix:
        removed = cleanup_image(f, bg_path)
        print(f"✓ Cleaned {Path(f).name}: removed {removed} pixels")

if __name__ == '__main__':
    main()
