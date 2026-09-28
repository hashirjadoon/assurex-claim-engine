import io
import re
from functools import lru_cache

import numpy as np
from PIL import Image


@lru_cache(maxsize=1)
def _reader():
    import easyocr
    return easyocr.Reader(["en"], gpu=False)


def extract_receipt_fields(image_bytes: bytes) -> dict:
    """OCR a receipt image and pull out key fields with regex. Images only."""
    img = np.array(Image.open(io.BytesIO(image_bytes)).convert("RGB"))
    text = "\n".join(_reader().readtext(img, detail=0))

    def find(pattern):
        m = re.search(pattern, text, re.IGNORECASE)
        return m.group(1).strip() if m else ""

    return {
        "raw_text": text,
        "purchase_date": find(r"(\d{4}-\d{2}-\d{2}|\d{2}[/-]\d{2}[/-]\d{4})"),
        "invoice_number": find(r"(?:invoice|inv)[\s#:.no]*([A-Z0-9-]{4,})"),
        "serial_number": find(r"(?:serial|s/n|sn)[\s#:.no]*([A-Z0-9-]{6,})"),
        "purchase_amount": find(r"(?:total|amount)[^\d]{0,10}(\d+[.,]?\d*)"),
        "retailer": text.split("\n")[0].strip() if text else "",
    }