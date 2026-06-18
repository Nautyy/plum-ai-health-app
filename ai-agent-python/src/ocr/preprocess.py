"""Lightweight image preprocessing before vision OCR."""

from __future__ import annotations

import base64
import io


def preprocess_image_base64(content_base64: str, mime_type: str = "image/jpeg") -> str:
    """
    Improve phone-photo bills: autocontrast + mild sharpen.
    Returns original base64 on any failure (graceful degradation).
    """
    try:
        from PIL import Image, ImageEnhance, ImageOps

        raw = base64.b64decode(content_base64)
        img = Image.open(io.BytesIO(raw))
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        img = ImageOps.autocontrast(img)
        img = ImageEnhance.Contrast(img).enhance(1.1)
        img = ImageEnhance.Sharpness(img).enhance(1.25)

        buf = io.BytesIO()
        use_jpeg = "jpeg" in (mime_type or "").lower() or "jpg" in (mime_type or "").lower()
        if use_jpeg:
            img.save(buf, format="JPEG", quality=92)
        else:
            img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return content_base64
