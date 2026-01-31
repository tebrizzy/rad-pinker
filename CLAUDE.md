# rad-background

Background replacement tool for PFP images.

## Usage

```bash
# Single image
python replace_background.py <input.png> <background.png> [output.png]

# Batch folder
python replace_background.py --batch <input_folder> <background.png> [output_folder]
```

## Important Rules

**NEVER create a new background image.** Always use the existing background file in this directory:
- `monolith_2000_centered.png` - The standard Monolith gradient background

The script auto-detects and removes solid color backgrounds from input images, then composites onto the specified background.

## Output Naming

- Single files: `<input_stem>_output.png`
- Batch mode: `<input_stem>_output.png` in output folder
