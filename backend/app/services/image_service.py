
"""
Image upload validation and storage.

Security-critical: this is the one place in the app that writes files to
disk based on public, untrusted input. Every check here exists to prevent
a specific attack:

- MIME type from magic bytes, not the client's Content-Type header
  (headers are trivially spoofable; the header claims what a file IS,
  magic bytes reveal what it actually IS).
- Size cap enforced server-side, not just trusted from Content-Length.
- Randomized storage filename, never the client-supplied one
  (prevents path traversal and filename collisions).
- Files are re-saved through Pillow (decode + re-encode), which strips
  EXIF metadata and any non-image payload smuggled inside an otherwise
  valid image file, and also guarantees the bytes on disk are genuinely
  a decodable image, not just something that passes a magic-byte sniff.
"""
import io
import os
import uuid

import magic
from fastapi import UploadFile, HTTPException, status
from PIL import Image
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.models import Project, ProjectImage

from app.ml.classifier import classify_image

settings = get_settings()


def _validate_and_reencode(raw_bytes: bytes) -> bytes:
    """Confirms the file is a real image of an allowed type and returns
    re-encoded, EXIF-stripped bytes safe to persist."""

    detected_type = magic.from_buffer(raw_bytes, mime=True)
    if detected_type not in settings.ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported image type: {detected_type}",
        )

    try:
        image = Image.open(io.BytesIO(raw_bytes))
        image.verify()  # raises if the file is corrupt / not a real image

        # verify() leaves the file object unusable for further ops, so
        # reopen before actually re-encoding
        image = Image.open(io.BytesIO(raw_bytes))
        image = image.convert("RGB")  # normalizes mode, drops alpha/ICC quirks

        output = io.BytesIO()
        image.save(output, format="JPEG", quality=85)  # re-encode strips EXIF
        return output.getvalue()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is not a valid, decodable image.",
        )


def save_project_image(db: Session, project: Project, upload: UploadFile) -> ProjectImage:
    raw_bytes = upload.file.read()

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(raw_bytes) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Image exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit.",
        )

    clean_bytes = _validate_and_reencode(raw_bytes)

    # Randomized filename — never derived from the client-supplied name.
    random_name = f"{uuid.uuid4()}.jpg"
    project_dir = os.path.join(settings.UPLOAD_STORAGE_PATH, project.id)
    os.makedirs(project_dir, exist_ok=True)
    storage_path = os.path.join(project_dir, random_name)

    with open(storage_path, "wb") as f:
        f.write(clean_bytes)

    try:
        predicted_category, predicted_confidence = classify_image(clean_bytes)
    except Exception:
        # Classification is a nice-to-have, not a hard requirement for
        # a successful upload — if the model fails for any reason, the
        # image should still save successfully rather than block the
        # whole request.
        predicted_category, predicted_confidence = None, None

    image_record = ProjectImage(
        project_id=project.id,
        storage_path=storage_path,
        original_filename=upload.filename or "unknown",
        content_type="image/jpeg",
        size_bytes=len(clean_bytes),
        predicted_category=predicted_category,
        predicted_confidence=predicted_confidence,
    )
    
    db.add(image_record)
    db.commit()
    db.refresh(image_record)

    return image_record
    