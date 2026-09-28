from src.rules_engine.warranty_rules import validate_claim
from src.rules_engine.contradiction_checks import detect_contradictions
from tests.helpers import make_claim


def test_valid_claim_passes():
    r = validate_claim(make_claim())
    assert r["status"] == "PASS"
    assert r["hard_fail_reasons"] == [] and r["manual_review_reasons"] == []


def test_expired_warranty_hard_fail():
    r = validate_claim(make_claim(claim_submission_date="2028-03-01", fault_occurrence_date="2028-02-28"))
    assert r["status"] == "HARD_FAIL"


def test_excluded_fault_hard_fail():
    r = validate_claim(make_claim(fault_type="Power Surge Damage"))
    assert r["status"] == "HARD_FAIL"
    assert any("Excluded" in x for x in r["hard_fail_reasons"])


def test_missing_documents_manual_review():
    r = validate_claim(make_claim(has_receipt=False, has_product_image=False))
    assert r["status"] == "MANUAL_REVIEW"
    assert set(r["missing_documents"]) == {"receipt", "product_image"}


def test_serial_mismatch_hard_fail_per_policy():
    r = validate_claim(make_claim(serial_number_match=False))
    assert any("Serial number mismatch" in x for x in r["hard_fail_reasons"] + r["manual_review_reasons"])


def test_prior_replacement_hard_fail():
    r = validate_claim(make_claim(previous_replacement=True))
    assert r["status"] == "HARD_FAIL"


def test_unauthorized_repair_manual_review():
    r = validate_claim(make_claim(repair_count=2, repair_authorized=False))
    assert r["status"] == "MANUAL_REVIEW"


def test_duplicate_manual_review():
    r = validate_claim(make_claim(is_duplicate_claim=True))
    assert r["status"] == "MANUAL_REVIEW" and r["duplicate"] is True


def test_ambiguous_description_manual_review():
    r = validate_claim(make_claim(fault_description="Works sometimes, not sure why"))
    assert r["status"] == "MANUAL_REVIEW"


def test_late_reporting_manual_review():
    r = validate_claim(make_claim(fault_occurrence_date="2026-04-01"))
    assert any("days after occurrence" in x for x in r["manual_review_reasons"])


# ---- boundary dates (expiry 2028-01-01, near-expiry window 7, grace 3) ----
def _at(claim_date, fault_date):
    return validate_claim(make_claim(claim_submission_date=claim_date, fault_occurrence_date=fault_date))


def test_boundary_8_days_before_expiry_is_active():
    assert _at("2027-12-24", "2027-12-23")["status"] == "PASS"


def test_boundary_7_days_before_expiry_is_manual():
    assert _at("2027-12-25", "2027-12-24")["status"] == "MANUAL_REVIEW"


def test_boundary_expiry_day_is_manual():
    assert _at("2028-01-01", "2027-12-31")["status"] == "MANUAL_REVIEW"


def test_boundary_grace_day_3_is_manual():
    assert _at("2028-01-04", "2028-01-03")["status"] == "MANUAL_REVIEW"


def test_boundary_grace_day_4_is_hard_fail():
    assert _at("2028-01-05", "2028-01-04")["status"] == "HARD_FAIL"


# ---- contradictions ----
def test_no_contradictions_on_clean_claim():
    assert detect_contradictions(make_claim()) == []


def test_claim_before_purchase():
    c = make_claim(claim_submission_date="2025-12-01", fault_occurrence_date="2025-11-30")
    assert any("before purchase" in x for x in detect_contradictions(c))


def test_fault_before_purchase():
    assert any("Fault date is before purchase" in x
               for x in detect_contradictions(make_claim(fault_occurrence_date="2025-12-01")))


def test_fault_after_claim():
    assert any("after claim submission" in x
               for x in detect_contradictions(make_claim(fault_occurrence_date="2026-06-20")))


def test_product_age_mismatch():
    assert any("Product age" in x for x in detect_contradictions(make_claim(product_age_days=5)))


def test_receipt_serial_conflict():
    assert any("Serial number on receipt" in x
               for x in detect_contradictions(make_claim(receipt_serial="SN-OTHER")))