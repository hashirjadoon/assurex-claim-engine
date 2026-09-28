from pathlib import Path
import numpy as np
from PIL import Image, ImageOps
from ai_edge_litert.interpreter import Interpreter

BASE_DIR = Path(__file__).resolve().parent.parent.parent
MODEL_PATH = BASE_DIR / "gtm_model" / "model_unquant.tflite"
LABELS_PATH = BASE_DIR / "gtm_model" / "labels.txt"

_interp = None
_in = None
_out = None
_labels = None


def _load():
    global _interp, _in, _out, _labels
    if _interp is not None:
        return
    _interp = Interpreter(model_path=str(MODEL_PATH))
    _interp.allocate_tensors()
    _in = _interp.get_input_details()
    _out = _interp.get_output_details()
    with open(LABELS_PATH) as f:
        _labels = [l.strip().split(" ", 1)[1] for l in f if l.strip()]


def classify_card(image_path: str) -> dict:
    """Independent GTM prediction. Never receives Python model output."""
    _load()
    h, w = int(_in[0]["shape"][1]), int(_in[0]["shape"][2])
    img = ImageOps.fit(Image.open(image_path).convert("RGB"), (w, h),
                       Image.Resampling.LANCZOS)
    arr = (np.asarray(img).astype(np.float32) / 127.5) - 1.0
    _interp.set_tensor(_in[0]["index"], np.expand_dims(arr, 0))
    _interp.invoke()
    scores = _interp.get_tensor(_out[0]["index"])[0]
    conf = {l: float(s) for l, s in zip(_labels, scores)}
    return {"predicted_class": max(conf, key=conf.get), "confidences": conf}


if __name__ == "__main__":
    import sys
    print(classify_card(sys.argv[1]))