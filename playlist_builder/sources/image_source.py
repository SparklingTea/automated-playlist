"""OCRs a playlist image (screenshot/photo) into raw text lines."""
import os

import pytesseract
from PIL import Image

_tesseract_cmd = os.environ.get("TESSERACT_CMD")
if _tesseract_cmd:
    pytesseract.pytesseract.tesseract_cmd = _tesseract_cmd


def extract_text(path: str) -> str:
    image = Image.open(path)
    return pytesseract.image_to_string(image)
