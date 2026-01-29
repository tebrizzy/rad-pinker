#!/usr/bin/env python3
"""
Remove isolated yellow dots/pixels from images.
These are leftover background pixels trapped inside the character.
"""

import sys
import math
from PIL import Image
from pathlib import Path
from collections import deque

YELLOW_TARGET = (252, 225, 132)
TOLERANCE = 40

def color_distance(c1, c2):
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(c1[:3], c2[:3])))

def is_yellow(pixel):
    if len(pixel) == 4 and pixel[3] == 0:
        return False
    return color_distance(pixel[:3], YELLOW_TARGET) < TOLERANCE

def find_yellow_clusters(img):
    """Find all clusters of yellow pixels."""
    pixels = img.load()
    width, height = img.size
    visited = set()
    clusters = []

    for y in range(height):
        for x in range(width):
            if (x, y) in visited:
                continue
            if not is_yellow(pixels[x, y]):
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
                if not is_yellow(pixels[cx, cy]):
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

def remove_small_clusters(input_path, output_path, max_cluster_size=50):
    """Remove yellow clusters smaller than max_cluster_size pixels."""
    img = Image.open(input_path).convert('RGBA')
    pixels = img.load()

    clusters = find_yellow_clusters(img)
    removed = 0

    for cluster in clusters:
        if len(cluster) <= max_cluster_size:
            # Small cluster - likely a leftover dot, make transparent
            for (x, y) in cluster:
                # Sample nearby non-yellow pixel to blend
                pixels[x, y] = (0, 0, 0, 0)
            removed += len(cluster)

    # Load background and composite
    bg_path = "/Users/zen/Desktop/solanamobi/radshader-hd-2026-01-29T12-24-24.png"
    background = Image.open(bg_path).convert('RGBA')
    background = background.resize(img.size, Image.Resampling.NEAREST)

    final = Image.alpha_composite(background, img)
    final.save(output_path, 'PNG')

    return removed

def main():
    if len(sys.argv) < 2:
        print("Usage: python remove_yellow_dots.py <image.png> [max_cluster_size]")
        sys.exit(1)

    input_file = sys.argv[1]
    max_size = int(sys.argv[2]) if len(sys.argv) > 2 else 50

    output_file = input_file  # Overwrite
    removed = remove_small_clusters(input_file, output_file, max_size)
    print(f"✓ Removed {removed} yellow pixels from {Path(input_file).name}")

if __name__ == '__main__':
    main()
