#!/usr/bin/env python3
"""
Generate thumbnails from assets/pictures to assets/thumbnails.
Compresses images to ~0.25MB at 1/4x resolution (1/16x total downsampling).
"""

import os
from pathlib import Path
from PIL import Image

# Source and destination directories
SOURCE_DIR = Path("assets/pictures")
OUTPUT_DIR = Path("assets/thumbnails")

# Target settings
TARGET_SIZE_BYTES = 250 * 1024  # ~0.25MB
SCALE_FACTOR = 0.25  # 1/4x on each dimension
QUALITY_START = 85  # Initial JPEG quality
QUALITY_STEP = 5  # Quality decrement step

# Supported image formats
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".JPG", ".JPEG", ".PNG"}


def resize_with_aspect_ratio(img, scale_factor):
    """Resize image maintaining aspect ratio."""
    new_width = int(img.width * scale_factor)
    new_height = int(img.height * scale_factor)
    return img.resize((new_width, new_height), Image.Resampling.LANCZOS)


def compress_to_target_size(img, target_bytes, initial_quality, quality_step):
    """
    Compress image to approximately target size by adjusting JPEG quality.
    Returns the bytes of the compressed image.
    """
    quality = initial_quality

    while quality > 10:  # Don't go below quality 10
        from io import BytesIO

        output = BytesIO()
        img.save(output, format="JPEG", quality=quality, optimize=True)
        size = output.tell()

        if size <= target_bytes:
            return output.getvalue()

        quality -= quality_step

    # If we couldn't get under target size, return lowest quality
    return output.getvalue()


def generate_thumbnails():
    """Generate thumbnails for all images in source directory."""
    if not SOURCE_DIR.exists():
        print(f"Error: Source directory '{SOURCE_DIR}' not found.")
        return

    # Create output directory
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Get all image files
    image_files = [
        f for f in SOURCE_DIR.iterdir()
        if f.is_file() and f.suffix in IMAGE_EXTENSIONS
    ]

    # Sort by filename
    image_files.sort(key=lambda x: x.name)

    print(f"Found {len(image_files)} images in '{SOURCE_DIR}'")
    print(f"Generating thumbnails at {SCALE_FACTOR}x resolution ({SCALE_FACTOR**2:.2%} area)...")
    print(f"Target size: ~{TARGET_SIZE_BYTES / 1024:.1f}KB per image\n")

    results = []

    for img_path in image_files:
        try:
            # Open image
            with Image.open(img_path) as img:
                original_size = img_path.stat().st_size
                original_dim = f"{img.height}x{img.width}"

                # Convert to RGB if necessary (for JPEG output)
                if img.mode not in ("RGB", "L"):
                    img = img.convert("RGB")

                # Resize to 1/4x dimensions
                resized = resize_with_aspect_ratio(img, SCALE_FACTOR)
                new_dim = f"{resized.height}x{resized.width}"

                # Compress to target size
                thumbnail_data = compress_to_target_size(
                    resized, TARGET_SIZE_BYTES, QUALITY_START, QUALITY_STEP
                )
                final_size = len(thumbnail_data)

                # Save thumbnail
                output_path = OUTPUT_DIR / f"{img_path.stem}.jpg"
                with open(output_path, "wb") as f:
                    f.write(thumbnail_data)

                # Calculate stats
                compression_ratio = original_size / final_size
                size_reduction = (1 - final_size / original_size) * 100

                results.append({
                    "name": img_path.name,
                    "original_dim": original_dim,
                    "new_dim": new_dim,
                    "original_size": original_size,
                    "final_size": final_size,
                    "compression_ratio": compression_ratio,
                })

                # Print result
                print(
                    f"✓ {img_path.name:30s} {original_dim:>9s} → {new_dim:>9s} | "
                    f"{original_size / 1024:6.1f}KB → {final_size / 1024:5.1f}KB "
                    f"({compression_ratio:.1f}x smaller, {size_reduction:.0f}% reduced)"
                )

        except Exception as e:
            print(f"✗ {img_path.name}: ERROR - {e}")

    # Print summary
    print(f"\n{'='*90}")
    print(f"Generated {len(results)} thumbnails in '{OUTPUT_DIR}'")

    if results:
        total_original = sum(r["original_size"] for r in results)
        total_final = sum(r["final_size"] for r in results)
        avg_compression = total_original / total_final

        print(f"Total original size: {total_original / 1024 / 1024:.1f}MB")
        print(f"Total thumbnail size: {total_final / 1024 / 1024:.1f}MB")
        print(f"Average compression: {avg_compression:.1f}x smaller")
        print(f"Space saved: {(1 - total_final / total_original) * 100:.0f}%")


if __name__ == "__main__":
    generate_thumbnails()
