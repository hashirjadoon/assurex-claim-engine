import hashlib
import json
import sys
import uuid
from datetime import date
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st
from src.auth import require_login
from src.db.db_utils import query, execute, log_action, notify
from src.rules_engine.warranty_rules import load_policy, validate_claim
from src.rules_engine.contradiction_checks import detect_contradictions
from src.ml.predict import predict_claim, get_model_version
from src.ml.gtm_client import classify_card
from src.decision.final_decision import make_final_decision
from src.cards.generate_card import render
from src.ocr.extract import extract_receipt_fields

st.set_page_config(page_title="New Claim", page_icon="📝", layout="wide")
user = require_login()

DAMAGE_TYPES = ["Manufacturing Defect", "Wear and Tear", "Accidental Damage",
                "Electrical Fault", "Structural Damage", "Cosmetic Damage"]
GTM_VERSION = "TeachableMachine v1.0 (model_unquant.tflite)"
UPLOAD_DIR = ROOT / "data" / "uploads"
STATUS_MAP = {"Likely Valid": "Approved", "Likely Invalid": "Rejected",
              "Manual Review Required": "Manual Review"}

st.title("Submit a Warranty Claim")

products = query(
    "SELECT p.*, w.warranty_id, w.duration_days, w.start_date, w.expiry_date FROM products p "
    "JOIN warranties w ON w.product_id = p.product_id WHERE (p.user_id = ? OR ? != 'customer')",
    (user["user_id"], user["role"]))
if not products:
    st.warning("Register a product first (Product Registration page).")
    st.stop()

labels = {f"{p['product_id']} - {p['product_name']} ({p['serial_number']})": p for p in products}
p = labels[st.selectbox("Product", list(labels))]
policy = load_policy(p["category"])

c1, c2 = st.columns(2)
fault_type = c1.selectbox("Fault type", policy["covered_faults"] + policy["exclusions"])
damage_type = c2.selectbox("Damage type", DAMAGE_TYPES)
desc = st.text_area("Fault description")
fault_date = c1.date_input("Fault occurrence date", value=date.today())
claim_date = c2.date_input("Claim submission date", value=date.today())
repair_count = c1.number_input("Previous repairs", 0, 10, 0)
repair_authorized = c2.checkbox("All repairs done by an authorized service center", True)
prev_repl = st.checkbox("Product was previously replaced")
serial_doc = st.text_input("Serial number shown on receipt / warranty card", value=p["serial_number"])

st.subheader("Documents")
d1, d2, d3 = st.columns(3)
receipt = d1.file_uploader("Purchase receipt", type=["pdf", "jpg", "jpeg", "png"])
wcard = d2.file_uploader("Warranty card", type=["pdf", "jpg", "jpeg", "png"])
pimg = d3.file_uploader("Product / damage image", type=["jpg", "jpeg", "png"])

rs = ""
if receipt is not None and receipt.type.startswith("image"):
    if st.button("Extract data from receipt (OCR)"):
        with st.spinner("Reading receipt (first run downloads OCR models)..."):
            st.session_state["ocr"] = extract_receipt_fields(receipt.getvalue())
elif receipt is not None:
    st.info("OCR supports image receipts only. Enter receipt details manually below.")

ocr = st.session_state.get("ocr", {})
if receipt is not None:
    st.subheader("Verify extracted receipt data")
    v1, v2, v3 = st.columns(3)
    v1.text_input("Purchase date", value=ocr.get("purchase_date", ""))
    v2.text_input("Invoice number", value=ocr.get("invoice_number", ""))
    rs = v3.text_input("Serial number on receipt", value=ocr.get("serial_number", ""))
    st.caption("Correct any wrong values before submitting.")



missing = [n for n, f in [("receipt", receipt), ("warranty card", wcard), ("product image", pimg)] if not f]
if missing:
    st.info("Missing documents: " + ", ".join(missing) + ". The claim may be sent for manual review.")

if st.button("Submit claim", type="primary"):
    claim_id = f"CLM-A{uuid.uuid4().hex[:7].upper()}"
    files = {"receipt": receipt, "warranty_card": wcard, "product_image": pimg}
    hashes = {k: hashlib.sha256(f.getvalue()).hexdigest() for k, f in files.items() if f}
    dup_doc = any(query("SELECT 1 FROM documents WHERE sha256=?", (h,)) for h in hashes.values())
    dup_claim = bool(query("SELECT 1 FROM claims WHERE product_id=? AND fault_type=?",
                           (p["product_id"], fault_type)))
    is_dup = dup_doc or dup_claim

    record = {
        "claim_id": claim_id, "product_id": p["product_id"], "product_category": p["category"],
        "product_name": p["product_name"], "serial_number": p["serial_number"],
        "purchase_date": p["purchase_date"], "purchase_price": p["purchase_price"],
        "warranty_start_date": p["start_date"], "warranty_duration_days": p["duration_days"],
        "warranty_expiry_date": p["expiry_date"],
        "fault_occurrence_date": fault_date.isoformat(), "fault_type": fault_type,
        "fault_description": desc, "damage_type": damage_type,
        "claim_submission_date": claim_date.isoformat(),
        "product_age_days": (claim_date - date.fromisoformat(p["purchase_date"])).days,
        "has_receipt": bool(receipt), "has_warranty_card": bool(wcard), "has_product_image": bool(pimg),
        "serial_number_match": serial_doc.strip() == p["serial_number"] and (not rs or rs.strip() == p["serial_number"]),
        "receipt_serial": rs.strip(),
        "repair_count": int(repair_count), "repair_authorized": repair_authorized,
        "previous_replacement": prev_repl, "is_duplicate_claim": is_dup,
    }

    with st.spinner("Analyzing claim..."):
        py = predict_claim(record)
        card_path = UPLOAD_DIR / "cards" / f"{claim_id}.png"
        card_path.parent.mkdir(parents=True, exist_ok=True)
        render(record, "#FFFFFF", 16, 6).save(card_path)
        gtm = classify_card(str(card_path))
        rules = validate_claim(record)
        contra = detect_contradictions(record)
        result = make_final_decision(py, gtm, rules, contra)

    decision = result["final_decision"]
    status = STATUS_MAP[decision]
    cmp_ = result["consistency"]

    execute("INSERT INTO claims (claim_id, user_id, product_id, fault_type, fault_description, damage_type, "
            "fault_date, claim_date, repair_count, repair_authorized, previous_replacement, serial_on_document, "
            "has_receipt, has_warranty_card, has_product_image, is_duplicate, status, card_path) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (claim_id, user["user_id"], p["product_id"], fault_type, desc, damage_type,
             fault_date.isoformat(), claim_date.isoformat(), int(repair_count), int(repair_authorized),
             int(prev_repl), serial_doc.strip(), int(bool(receipt)), int(bool(wcard)), int(bool(pimg)),
             int(is_dup), status, str(card_path)))

    for k, f in files.items():
        if f:
            fp = UPLOAD_DIR / claim_id / f.name
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_bytes(f.getvalue())
            execute("INSERT INTO documents (claim_id, doc_type, filename, file_path, sha256) VALUES (?,?,?,?,?)",
                    (claim_id, k, f.name, str(fp), hashes[k]))

    pc, gc = py["confidences"], gtm["confidences"]
    execute("INSERT INTO predictions (claim_id, python_class, py_conf_valid, py_conf_invalid, py_conf_manual, "
            "gtm_class, gtm_conf_valid, gtm_conf_invalid, gtm_conf_manual, class_match, confidence_difference, "
            "consistency_status, rule_status, rules_json, contradictions_json, final_decision, explanation_json, "
            "python_model_version, gtm_model_version) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (claim_id, py["predicted_class"], pc["Valid"], pc["Invalid"], pc["ManualReview"],
             gtm["predicted_class"], gc["Valid"], gc["Invalid"], gc["ManualReview"],
             int(cmp_["class_match"]), cmp_["confidence_difference"], cmp_["consistency_status"],
             rules["status"], json.dumps(rules), json.dumps(contra), decision,
             json.dumps(result["explanation"]), get_model_version(), GTM_VERSION))

    log_action(user["user_id"], "submit_claim", "claim", claim_id)
    log_action(user["user_id"], "model_prediction", "claim", claim_id, f"{decision} | {cmp_['consistency_status']}")
    notify(user["user_id"], f"Claim {claim_id} submitted. Result: {decision} (status: {status})")

    st.subheader(f"Claim {claim_id}")
    (st.success if decision == "Likely Valid" else st.error if decision == "Likely Invalid" else st.warning)(
        f"Final decision: {decision}")

    m1, m2, m3 = st.columns(3)
    m1.metric("Python model", py["predicted_class"], f"{max(pc.values()):.0%}")
    m2.metric("GTM model", gtm["predicted_class"], f"{max(gc.values()):.0%}")
    m3.metric("Confidence difference", f"{cmp_['confidence_difference']:.2f}", cmp_["consistency_status"])

    st.dataframe(pd.DataFrame({"Python": pc, "GTM": gc}).style.format("{:.1%}"))
    st.image(str(card_path), caption="Claim Summary Card", width=300)

    ex = result["explanation"]
    e1, e2 = st.columns(2)
    with e1:
        st.markdown("**Supporting factors / rules passed**")
        for s in ex["supporting"]:
            st.write("✅", s)
    with e2:
        st.markdown("**Opposing factors / rules failed**")
        for s in ex["opposing"] + ex["contradictions"]:
            st.write("⚠️", s)
    if ex["additional_evidence_required"]:
        st.info("Additional evidence required: " + ", ".join(ex["additional_evidence_required"]))