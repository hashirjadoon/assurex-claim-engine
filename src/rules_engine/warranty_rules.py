import json
from datetime import datetime
from pathlib import Path

POLICY_DIR = Path(__file__).resolve().parent.parent.parent / "policies"
POLICY_FILES = {
    "Electronics": "electronics_policy.json",
    "Appliances": "appliances_policy.json",
    "Furniture": "furniture_policy.json",
}
DOC_FIELDS = {"receipt": "has_receipt", "warranty_card": "has_warranty_card",
              "product_image": "has_product_image"}


def load_policy(category: str) -> dict:
    with open(POLICY_DIR / POLICY_FILES[category]) as f:
        return json.load(f)


def _d(s):
    return datetime.strptime(str(s)[:10], "%Y-%m-%d")


def validate_claim(claim: dict) -> dict:
    p = load_policy(claim["product_category"])
    passed, hard_fail, manual = [], [], []
    missing_docs = []

    days_left = (_d(claim["warranty_expiry_date"]) - _d(claim["claim_submission_date"])).days
    if days_left >= 0:
        if days_left <= p["near_expiry_window_days"]:
            manual.append(f"Claim filed {days_left} days before warranty expiry")
        else:
            passed.append("Warranty active")
    elif abs(days_left) <= p["grace_period_days"]:
        manual.append(f"Claim filed {abs(days_left)} days after expiry (grace period)")
    else:
        hard_fail.append(f"Warranty expired {abs(days_left)} days ago")

    fault = claim["fault_type"]
    if fault in p["exclusions"]:
        hard_fail.append(f"Excluded fault: {fault}")
    elif fault in p["covered_faults"]:
        passed.append("Fault is covered")
    else:
        manual.append(f"Fault not listed as covered: {fault}")

    desc = str(claim.get("fault_description", "")).lower()
    if any(k in desc for k in p["ambiguous_keywords"]):
        manual.append("Ambiguous fault description")

    for doc in p["mandatory_documents"]:
        if not claim[DOC_FIELDS[doc]]:
            missing_docs.append(doc)
    if missing_docs:
        manual.append("Missing mandatory documents: " + ", ".join(missing_docs))
    else:
        passed.append("All mandatory documents present")

    if not claim["serial_number_match"]:
        (hard_fail if p["serial_mismatch_action"] == "hard_fail" else manual).append("Serial number mismatch")
    else:
        passed.append("Serial number matches")

    if claim["previous_replacement"] and not p["allow_claim_after_replacement"]:
        hard_fail.append("Replacement already used")
    else:
        passed.append("No prior replacement")

    if claim["repair_count"] > 0 and not claim["repair_authorized"]:
        manual.append("Repair done by unauthorized service center")
    else:
        passed.append("Repair history acceptable")

    if claim["is_duplicate_claim"]:
        manual.append("Possible duplicate claim")

    reporting_days = (_d(claim["claim_submission_date"]) - _d(claim["fault_occurrence_date"])).days
    if reporting_days > p["claim_reporting_period_days"]:
        manual.append(f"Fault reported {reporting_days} days after occurrence")

    status = "HARD_FAIL" if hard_fail else "MANUAL_REVIEW" if manual else "PASS"
    return {"status": status, "rules_passed": passed, "hard_fail_reasons": hard_fail,
            "manual_review_reasons": manual, "missing_documents": missing_docs,
            "duplicate": bool(claim["is_duplicate_claim"])}