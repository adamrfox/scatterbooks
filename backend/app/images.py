import io
import shutil
from pathlib import Path

from PIL import Image, ImageOps

from app.config import settings

THUMBNAIL_SIZE = (400, 400)
IDENTIFICATION_MAX_SIZE = (1024, 1024)
JPEG_QUALITY = 85
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}


class ImageProcessingError(ValueError):
    pass


def _validate_and_normalize(raw_bytes: bytes) -> Image.Image:
    """Shared validation + EXIF correction for any uploaded image, whether
    it's being stored as a book photo or just sent off for one-shot AI
    identification. Raises ImageProcessingError for any invalid/oversized/
    unsupported upload.
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

    return image


def process_upload(raw_bytes: bytes) -> tuple[bytes, bytes, int, int]:
    """Validate and normalize an uploaded image.

    Returns (full_jpeg_bytes, thumb_jpeg_bytes, width, height) of the
    EXIF-corrected, re-encoded image. Raises ImageProcessingError for any
    invalid/oversized/unsupported upload.
    """
    image = _validate_and_normalize(raw_bytes)
    width, height = image.size

    full_buffer = io.BytesIO()
    image.save(full_buffer, format="JPEG", quality=JPEG_QUALITY)

    thumbnail = image.copy()
    thumbnail.thumbnail(THUMBNAIL_SIZE)
    thumb_buffer = io.BytesIO()
    thumbnail.save(thumb_buffer, format="JPEG", quality=JPEG_QUALITY)

    return full_buffer.getvalue(), thumb_buffer.getvalue(), width, height


def prepare_for_identification(raw_bytes: bytes) -> bytes:
    """Validate and downscale an image for a one-off AI identification
    call. Never persisted to disk -- 1024px is plenty to read a cover, and
    keeps the request small/fast/cheap.
    """
    image = _validate_and_normalize(raw_bytes)
    image.thumbnail(IDENTIFICATION_MAX_SIZE)
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=JPEG_QUALITY)
    return buffer.getvalue()


def book_image_dir(book_id: int) -> Path:
    return Path(settings.images_dir) / str(book_id)


def full_image_path(book_id: int, image_id: int) -> Path:
    return book_image_dir(book_id) / f"{image_id}_full.jpg"


def thumb_image_path(book_id: int, image_id: int) -> Path:
    return book_image_dir(book_id) / f"{image_id}_thumb.jpg"


def delete_book_image_directory(book_id: int) -> None:
    shutil.rmtree(book_image_dir(book_id), ignore_errors=True)


def wish_list_entry_image_dir(entry_id: int) -> Path:
    # Nested under a distinct subdirectory so entry IDs never collide with
    # book IDs in the same path namespace -- both are autoincrementing from 1.
    return Path(settings.images_dir) / "wishlist_entries" / str(entry_id)


def wish_list_entry_full_image_path(entry_id: int, image_id: int) -> Path:
    return wish_list_entry_image_dir(entry_id) / f"{image_id}_full.jpg"


def wish_list_entry_thumb_image_path(entry_id: int, image_id: int) -> Path:
    return wish_list_entry_image_dir(entry_id) / f"{image_id}_thumb.jpg"


def delete_wish_list_entry_image_directory(entry_id: int) -> None:
    shutil.rmtree(wish_list_entry_image_dir(entry_id), ignore_errors=True)
