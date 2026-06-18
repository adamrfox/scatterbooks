import io
import shutil
from pathlib import Path

from PIL import Image, ImageOps

from app.config import settings

THUMBNAIL_SIZE = (400, 400)
JPEG_QUALITY = 85
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}


class ImageProcessingError(ValueError):
    pass


def process_upload(raw_bytes: bytes) -> tuple[bytes, bytes, int, int]:
    """Validate and normalize an uploaded image.

    Returns (full_jpeg_bytes, thumb_jpeg_bytes, width, height) of the
    EXIF-corrected, re-encoded image. Raises ImageProcessingError for any
    invalid/oversized/unsupported upload.
    """
    if len(raw_bytes) > settings.max_upload_mb * 1024 * 1024:
        raise ImageProcessingError(f"Image exceeds the {settings.max_upload_mb}MB limit")

    try:
        probe = Image.open(io.BytesIO(raw_bytes))
        image_format = probe.format
        probe.verify()
    except Exception as exc:
        raise ImageProcessingError("File is not a valid image") from exc

    if image_format not in ALLOWED_FORMATS:
        raise ImageProcessingError(
            f"Unsupported image format: {image_format}. Allowed formats: "
            f"{', '.join(sorted(ALLOWED_FORMATS))}"
        )

    try:
        image = Image.open(io.BytesIO(raw_bytes))
        image = ImageOps.exif_transpose(image)
        if image.mode != "RGB":
            image = image.convert("RGB")
    except Exception as exc:
        raise ImageProcessingError("Could not process image") from exc

    width, height = image.size

    full_buffer = io.BytesIO()
    image.save(full_buffer, format="JPEG", quality=JPEG_QUALITY)

    thumbnail = image.copy()
    thumbnail.thumbnail(THUMBNAIL_SIZE)
    thumb_buffer = io.BytesIO()
    thumbnail.save(thumb_buffer, format="JPEG", quality=JPEG_QUALITY)

    return full_buffer.getvalue(), thumb_buffer.getvalue(), width, height


def book_image_dir(book_id: int) -> Path:
    return Path(settings.images_dir) / str(book_id)


def full_image_path(book_id: int, image_id: int) -> Path:
    return book_image_dir(book_id) / f"{image_id}_full.jpg"


def thumb_image_path(book_id: int, image_id: int) -> Path:
    return book_image_dir(book_id) / f"{image_id}_thumb.jpg"


def delete_book_image_directory(book_id: int) -> None:
    shutil.rmtree(book_image_dir(book_id), ignore_errors=True)
