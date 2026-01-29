#!/usr/bin/env python3
"""
Rad Pinker - Apply pink background to character images
Usage: python rad_pinker.py character1.png character2.png ...
"""

from PIL import Image
import os
import sys

def apply_pink_background(character_path, background_path, output_dir):
    """Places a character image on top of a pink background."""
    bg = Image.open(background_path).convert("RGBA")
    character = Image.open(character_path).convert("RGBA")

    # Resize background to match character size
    bg_resized = bg.resize(character.size)

    # Paste character on top using its alpha as mask
    bg_resized.paste(character, (0, 0), character)

    # Create output filename
    name = os.path.splitext(os.path.basename(character_path))[0]
    output_path = os.path.join(output_dir, f"{name}_pink.png")

    bg_resized.save(output_path, "PNG")
    print(f"Saved: {output_path}")
    return output_path


def main():
    # Get script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    bg_path = os.path.join(script_dir, "pink_background.png")

    # Check background exists
    if not os.path.exists(bg_path):
        print("Error: pink_background.png not found in script directory")
        sys.exit(1)

    # Get input files from command line or current directory
    if len(sys.argv) > 1:
        files = sys.argv[1:]
    else:
        # Process all PNGs in current directory
        files = [f for f in os.listdir('.') if f.lower().endswith('.png') and not f.endswith('_pink.png')]

    if not files:
        print("Usage: python rad_pinker.py character1.png character2.png ...")
        print("Or place PNG files in the same directory and run without arguments")
        sys.exit(1)

    # Create output directory
    output_dir = os.path.join(os.getcwd(), "pink_output")
    os.makedirs(output_dir, exist_ok=True)

    # Process each file
    for f in files:
        if os.path.exists(f):
            try:
                apply_pink_background(f, bg_path, output_dir)
            except Exception as e:
                print(f"Error processing {f}: {e}")
        else:
            print(f"File not found: {f}")

    print(f"\nDone! Check the 'pink_output' folder")


if __name__ == "__main__":
    main()
