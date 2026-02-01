RAD BACKGROUND CHANGER
======================

Applies whatever background image you have to character images. Auto-detects and removes the original background, then composites onto your new background.

REQUIREMENTS:
- Python 3
- Pillow: pip install Pillow

USAGE:
  Single image:
    python replace_background.py <input.png> <background.png> [output.png]

  Batch folder:
    python replace_background.py --batch <input_folder> <background.png> [output_folder]

EXAMPLES:
  python replace_background.py wizard.png monolith_2000_centered.png wizard_output.png
  python replace_background.py --batch ./characters monolith_2000_centered.png ./output

Works with both transparent and solid-color backgrounds - the script auto-detects and handles both.
