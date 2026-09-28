from datetime import datetime


def _d(s):
    return datetime.strptime(str(s)[:10], "%Y-%m-%d")


def detect_contradictions(claim: dict) -> list:
    found = []
    purchase = _d(claim["purchase_date"])
    submitted = _d(claim["claim_submission_date"])
    fault = _d(claim["fault_occurrence_date"])

    if submitted < purchase:
        found.append("Claim submission date is before purchase date")
    if fault < purchase:
        found.append("Fault date is before purchase date")
    if fault > submitted:
        found.append("Fault date is after claim submission date")
    if (submitted - purchase).days != int(claim["product_age_days"]):
        found.append("Product age does not match purchase and claim dates")
    receipt_serial = claim.get("receipt_serial")
    if receipt_serial and receipt_serial != claim["serial_number"]:
        found.append("Serial number on receipt differs from entered serial number")
    return found