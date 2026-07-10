#!/usr/bin/env python3
"""
Analyze image dimensions in assets/pictures directory.
Outputs format: <name> <dim> (height x width)
"""

import os
from pathlib import Path
from PIL import Image

# Target directory
PICTURES_DIR = Path("assets/pictures")

# Supported image formats
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".JPG", ".JPEG", ".PNG"}


def analyze_images():
    """Scan pictures directory and output image dimensions."""
    if not PICTURES_DIR.exists():
        print(f"Error: Directory '{PICTURES_DIR}' not found.")
        return

    # Get all image files
    image_files = [
        f for f in PICTURES_DIR.iterdir()
        if f.is_file() and f.suffix in IMAGE_EXTENSIONS
    ]

    # Sort by filename
    image_files.sort(key=lambda x: x.name)

    print(f"Found {len(image_files)} images in '{PICTURES_DIR}':\n")

    for img_path in image_files:
        try:
            with Image.open(img_path) as img:
                width, height = img.size
                print(f"{img_path.name} {height}x{width}")
        except Exception as e:
            print(f"{img_path.name} ERROR: {e}")


if __name__ == "__main__":
    analyze_images()
