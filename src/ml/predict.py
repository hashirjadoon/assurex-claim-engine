import json
from pathlib import Path

import joblib
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent.parent
MODEL_PATH = BASE_DIR / "model" / "claim_classifier.pkl"
ENC_PATH = BASE_DIR / "model" / "encoders.pkl"
META_PATH = BASE_DIR / "model" / "model_metadata.json"

CATEGORICAL = ["product_category", "fault_type", "damage_type"]
BOOLEAN = ["has_receipt", "has_warranty_card", "has_product_image",
           "serial_number_match", "repair_authorized",
           "previous_replacement", "is_duplicate_claim"]
NUMERIC = ["product_age_days", "warranty_duration_days", "repair_count",
           "purchase_price"]

_model = None
_bundle = None
_meta = None


def _load():
    global _model, _bundle, _meta
    if _model is not None:
        return
    _model = joblib.load(MODEL_PATH)
    _bundle = joblib.load(ENC_PATH)
    with open(META_PATH) as f:
        _meta = json.load(f)


def get_model_version() -> str:
    _load()
    return f"{_meta['model_name']} v{_meta['model_version']}"


def predict_claim(claim: dict) -> dict:
    """Independent Python-model prediction. Never receives GTM output."""
    _load()
    enc = _bundle["encoders"]
    row = pd.DataFrame([claim])

    for col in CATEGORICAL:
        if claim[col] not in enc[col].classes_:
            raise ValueError(f"Unknown value '{claim[col]}' for {col}")
        row[col] = enc[col].transform(row[col])
    for col in BOOLEAN:
        row[col] = row[col].astype(int)

    row = row[_bundle["feature_columns"]]
    row[NUMERIC] = _bundle["scaler"].transform(row[NUMERIC])

    probs = _model.predict_proba(row)[0]
    classes = enc["class_label"].classes_
    conf = {c: float(p) for c, p in zip(classes, probs)}
    return {"predicted_class": max(conf, key=conf.get), "confidences": conf}


if __name__ == "__main__":
    df = pd.read_csv(BASE_DIR / "data" / "processed" / "test.csv")
    claim = df.iloc[0].to_dict()
    print("Actual:", claim["class_label"])
    print(predict_claim(claim))
    print(get_model_version())