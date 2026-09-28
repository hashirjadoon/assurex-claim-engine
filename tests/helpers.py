from datetime import datetime


def make_claim(**over):
    c = dict(
        claim_id="CLM-TEST01", product_id="PRD-TEST01", product_category="Appliances",
        product_name="Refrigerator", serial_number="SN-TEST000001",
        purchase_date="2026-01-01", purchase_price=500.0,
        warranty_start_date="2026-01-01", warranty_duration_days=730,
        warranty_expiry_date="2028-01-01",
        fault_occurrence_date="2026-06-08", fault_type="Motor Failure",
        fault_description="Motor stopped running.", damage_type="Manufacturing Defect",
        claim_submission_date="2026-06-10",
        has_receipt=True, has_warranty_card=True, has_product_image=True,
        serial_number_match=True, repair_count=0, repair_authorized=True,
        previous_replacement=False, is_duplicate_claim=False, receipt_serial="",
    )
    c.update(over)
    if "product_age_days" not in over:
        d = lambda s: datetime.strptime(s, "%Y-%m-%d")
        c["product_age_days"] = (d(c["claim_submission_date"]) - d(c["purchase_date"])).days
    return c


def preds(cls, conf, other=None):
    rest = (1 - conf) / 2
    conf_map = {k: rest for k in ("Valid", "Invalid", "ManualReview")}
    conf_map[cls] = conf
    return {"predicted_class": cls, "confidences": conf_map}