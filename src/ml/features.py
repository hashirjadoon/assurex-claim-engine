import pandas as pd

DOC_COLS = ["has_receipt", "has_warranty_card", "has_product_image"]


def add_derived_features(df: pd.DataFrame) -> pd.DataFrame:
    """Derived fields required by the SRS: remaining warranty period and missing-document count."""
    out = df.copy()
    out["remaining_warranty_days"] = out["warranty_duration_days"] - out["product_age_days"]
    out["missing_doc_count"] = 3 - out[DOC_COLS].astype(int).sum(axis=1)
    return out