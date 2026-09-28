"""SRS 1.10 item 8: the 11 required scenarios + security, database, negative, OCR tests.
Put this file in tests/  and run:  pytest -v | tee reports/test_results.txt
"""
import io
import pytest
from tests.helpers import make_claim, preds
from src.rules_engine.warranty_rules import validate_claim, load_policy
from src.rules_engine.contradiction_checks import detect_contradictions
from src.decision.final_decision import make_final_decision, compare_models
from src.db import db_utils


def run(claim, py, gtm):
    rules = validate_claim(claim)
    contra = detect_contradictions(claim)
    return rules, contra, make_final_decision(py, gtm, rules, contra)


# ---------- 11 REQUIRED SCENARIOS ----------
def test_s01_valid_claim():
    _, _, d = run(make_claim(), preds("Valid", 0.9), preds("Valid", 0.88))
    assert d["final_decision"] == "Likely Valid"

def test_s02_invalid_claim():
    c = make_claim(fault_type="Rust/Corrosion")
    _, _, d = run(c, preds("Invalid", 0.9), preds("Invalid", 0.85))
    assert d["final_decision"] == "Likely Invalid"

def test_s03_manual_review_claim():
    c = make_claim(fault_description="Works sometimes, not sure why")
    _, _, d = run(c, preds("ManualReview", 0.8), preds("ManualReview", 0.75))
    assert d["final_decision"] == "Manual Review Required"

def test_s04_expired_warranty():
    r, _, _ = run(make_claim(warranty_expiry_date="2026-05-01"),
                  preds("Invalid", 0.9), preds("Invalid", 0.9))
    assert r["status"] == "HARD_FAIL"
    assert any("expired" in x for x in r["hard_fail_reasons"])

def test_s05_missing_document():
    r, _, d = run(make_claim(has_warranty_card=False), preds("Valid", 0.9), preds("Valid", 0.9))
    assert "warranty_card" in r["missing_documents"]
    assert d["final_decision"] == "Manual Review Required"

def test_s06_duplicate_claim():
    r, _, d = run(make_claim(is_duplicate_claim=True), preds("Valid", 0.9), preds("Valid", 0.9))
    assert r["duplicate"] is True
    assert d["final_decision"] == "Manual Review Required"

def test_s07_contradictory_claim():
    c = make_claim(fault_occurrence_date="2026-06-20")  # fault after claim date
    _, contra, d = run(c, preds("Valid", 0.9), preds("Valid", 0.9))
    assert contra
    assert d["final_decision"] == "Manual Review Required"

def test_s08_serial_number_mismatch():
    c = make_claim(serial_number_match=False, receipt_serial="SN-OTHER")
    r, contra, _ = run(c, preds("Invalid", 0.9), preds("Invalid", 0.9))
    assert "Serial number mismatch" in r["hard_fail_reasons"]
    assert any("Serial number on receipt" in x for x in contra)

def test_s09_unauthorized_repair():
    r, _, d = run(make_claim(repair_count=1, repair_authorized=False),
                  preds("Valid", 0.9), preds("Valid", 0.9))
    assert any("unauthorized" in x for x in r["manual_review_reasons"])
    assert d["final_decision"] == "Manual Review Required"

def test_s10_tricky_boundary_date():
    r, _, _ = run(make_claim(warranty_expiry_date="2026-06-17"),   # exactly 7 days left
                  preds("Valid", 0.9), preds("Valid", 0.9))
    assert r["status"] == "MANUAL_REVIEW"
    r2, _, _ = run(make_claim(warranty_expiry_date="2026-06-18"),  # 8 days left
                   preds("Valid", 0.9), preds("Valid", 0.9))
    assert r2["status"] == "PASS"

def test_s11_model_disagreement():
    _, _, d = run(make_claim(), preds("Valid", 0.9), preds("Invalid", 0.8))
    assert d["consistency"]["consistency_status"] == "Model Disagreement"
    assert d["final_decision"] == "Manual Review Required"


# ---------- NEGATIVE / BOUNDARY ----------
def test_unknown_category_raises():
    with pytest.raises(KeyError):
        load_policy("Spaceships")

def test_bad_date_format_raises():
    with pytest.raises(ValueError):
        detect_contradictions(make_claim(purchase_date="01/01/2026"))

def test_confidence_exactly_at_min_is_not_uncertain():
    r = compare_models(preds("Valid", 0.55), preds("Valid", 0.55))
    assert r["consistency_status"] == "Strong Match"

def test_confidence_just_below_min_is_uncertain():
    r = compare_models(preds("Valid", 0.54), preds("Valid", 0.9))
    assert r["consistency_status"] == "Uncertain Result"


# ---------- SECURITY + DATABASE (uses a temporary DB, real DB untouched) ----------
@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db_utils, "DB_PATH", tmp_path / "test.db")
    db_utils.init_db()
    return db_utils

def test_db_default_users_created(tmp_db):
    assert {u["username"] for u in tmp_db.query("SELECT username FROM users")} >= {"admin", "reviewer", "demo"}

def test_db_correct_password_logs_in(tmp_db):
    assert tmp_db.verify_user("admin", "Admin@123")["role"] == "admin"

def test_sec_wrong_password_rejected(tmp_db):
    assert tmp_db.verify_user("admin", "wrong") is None

def test_sec_unknown_user_rejected(tmp_db):
    assert tmp_db.verify_user("ghost", "x") is None

def test_sec_password_not_stored_plaintext(tmp_db):
    row = tmp_db.query("SELECT * FROM users WHERE username='admin'")[0]
    assert "Admin@123" not in str(row.values())
    assert len(row["password_hash"]) == 64

def test_sec_unique_salts(tmp_db):
    tmp_db.create_user("a1", "same", "customer"); tmp_db.create_user("a2", "same", "customer")
    h = [r["password_hash"] for r in tmp_db.query("SELECT password_hash FROM users WHERE username IN ('a1','a2')")]
    assert h[0] != h[1]

def test_sec_sql_injection_login_fails(tmp_db):
    assert tmp_db.verify_user("admin' OR '1'='1", "x") is None
    assert tmp_db.verify_user("admin'--", "x") is None

def test_db_duplicate_username_rejected(tmp_db):
    assert tmp_db.create_user("admin", "x", "customer") is False

def test_db_audit_log_and_notification(tmp_db):
    uid = tmp_db.query("SELECT user_id FROM users WHERE username='demo'")[0]["user_id"]
    tmp_db.log_action(uid, "TEST_ACTION", "claim", "CLM-1", "details")
    tmp_db.notify(uid, "hello")
    assert tmp_db.query("SELECT 1 FROM audit_log WHERE action='TEST_ACTION'")
    assert tmp_db.query("SELECT 1 FROM notifications WHERE message='hello'")


# ---------- OCR ----------
def test_ocr_rejects_non_image():
    pytest.importorskip("easyocr")
    from src.ocr.extract import extract_receipt_fields
    with pytest.raises(Exception):
        extract_receipt_fields(b"not an image")

def test_ocr_returns_expected_keys():
    pytest.importorskip("easyocr")
    from PIL import Image, ImageDraw, ImageFont
    from src.ocr.extract import extract_receipt_fields
    img = Image.new("RGB", (900, 300), "white")
    ImageDraw.Draw(img).text((20, 60), "Invoice No: INV-12345  Serial: SN-ABC12345  Total 500.00  2026-01-01",
                             fill="black", font=ImageFont.load_default(size=28))
    buf = io.BytesIO(); img.save(buf, "PNG")
    out = extract_receipt_fields(buf.getvalue())
    assert {"purchase_date", "invoice_number", "serial_number", "purchase_amount", "retailer"} <= set(out)