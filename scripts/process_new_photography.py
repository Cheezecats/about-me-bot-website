"""Optimize the newly imported photography assets for the web.

The source JPEGs are copied into public/assets/pictures first. This script
re-encodes only the listed new files as moderately compressed full images and
creates smaller gallery thumbnails alongside them.
"""

from pathlib import Path

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[1]
PICTURES = ROOT / "public" / "assets" / "pictures"
THUMBNAILS = ROOT / "public" / "assets" / "thumbnails"

NEW_FILES = [
    "sea-ship.jpg",
    "hakuba-01.jpg",
    "stars-night.jpg",
    "tokyo-tower-night.jpg",
    "hakuba-02.jpg",
    "hakuba-03.jpg",
    "ueno-02.jpg",
    "xinjiang-dunes-abstract.jpg",
    "hakuba-04.jpg",
    "ueno-01.jpg",
    "xinjiang-dunes.jpg",
    "shiga-night.jpg",
    "karuizawa-forest.jpg",
    "xinjiang-canyon.jpg",
    "karuizawa-frozen-stream.jpg",
]


def save_jpeg(image: Image.Image, destination: Path, *, quality: int) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    image = ImageOps.exif_transpose(image).convert("RGB")
    image.save(destination, "JPEG", quality=quality, optimize=True, progressive=True)


def resize_max(image: Image.Image, max_dimension: int) -> Image.Image:
    copy = image.copy()
    copy.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
    return copy


def process(filename: str) -> None:
    source = PICTURES / filename
    thumbnail = THUMBNAILS / filename
    if not source.exists():
        raise FileNotFoundError(source)

    with Image.open(source) as image:
        full = resize_max(image, 3200)
        thumb = resize_max(image, 900)

    # Write beside the source before replacing it, so a failed encode cannot
    # destroy the imported copy.
    temporary = source.with_suffix(".optimized.jpg")
    save_jpeg(full, temporary, quality=88)
    # OneDrive can briefly hold a newly copied file open. Removing the copied
    # source before moving the finished file is more tolerant of that behavior
    # than replacing it atomically on Windows.
    source.unlink()
    temporary.rename(source)
    save_jpeg(thumb, thumbnail, quality=82)


def main() -> None:
    for filename in NEW_FILES:
        process(filename)
        print(f"processed {filename}")


if __name__ == "__main__":
    main()
