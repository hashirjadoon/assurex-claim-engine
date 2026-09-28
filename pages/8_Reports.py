import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st
from src.auth import require_login
from src.db.db_utils import claim_overview, query, log_action


st.set_page_config(page_title="Reports", page_icon="📄", layout="wide")
user = require_login()
st.title("Search, Reports and Export")

rows = claim_overview("c.user_id = ?", (user["user_id"],)) if user["role"] == "customer" else claim_overview()
if not rows:
    st.info("No claims yet.")
    st.stop()
df = pd.DataFrame(rows)

c1, c2, c3, c4 = st.columns(4)
q = c1.text_input("Claim ID / Product ID / Serial")
cat = c2.selectbox("Category", ["All"] + sorted(df.category.dropna().unique().tolist()))
stt = c3.selectbox("Status", ["All"] + sorted(df.status.dropna().unique().tolist()))
dec = c4.selectbox("Decision", ["All"] + sorted(df.final_decision.dropna().unique().tolist()))
if q:
    df = df[df.claim_id.str.contains(q, case=False) | df.product_id.str.contains(q, case=False)
            | df.serial_number.str.contains(q, case=False)]
if cat != "All":
    df = df[df.category == cat]
if stt != "All":
    df = df[df.status == stt]
if dec != "All":
    df = df[df.final_decision == dec]
st.dataframe(df.drop(columns=["explanation_json", "contradictions_json", "card_path"]), use_container_width=True)

if not df.empty:
    st.subheader("Downloadable claim report")
    cid = st.selectbox("Claim", df.claim_id.tolist())
    c = df[df.claim_id == cid].iloc[0]
    ex = json.loads(c.explanation_json or "{}")
    reviews = query("SELECT action, comment, created_at FROM reviews WHERE claim_id=?", (cid,))
    docs = query("SELECT doc_type, filename FROM documents WHERE claim_id=?", (cid,))
    lines = [
        f"CLAIM REPORT: {cid}", "=" * 50,
        f"Product: {c.product_id} ({c.category}) | Serial: {c.serial_number}",
        f"Fault: {c.fault_type} | Claim date: {c.claim_date} | Status: {c.status}",
        "", "UPLOADED EVIDENCE"] + [f"- {d['doc_type']}: {d['filename']}" for d in docs] + [
        "", "MODEL RESULTS",
        f"Python model: {c.python_class} (Valid {c.py_conf_valid:.1%}, Invalid {c.py_conf_invalid:.1%}, Manual {c.py_conf_manual:.1%})",
        f"GTM model: {c.gtm_class} (Valid {c.gtm_conf_valid:.1%}, Invalid {c.gtm_conf_invalid:.1%}, Manual {c.gtm_conf_manual:.1%})",
        f"Class match: {bool(c.class_match)} | Confidence difference: {c.confidence_difference:.3f} | {c.consistency_status}",
        f"Model versions: {c.python_model_version} / {c.gtm_model_version}",
        "", f"RULE VALIDATION: {c.rule_status}"] + [f"+ {s}" for s in ex.get("supporting", [])] + [
        f"- {s}" for s in ex.get("opposing", [])] + [
        "", "CONTRADICTIONS"] + [f"- {s}" for s in ex.get("contradictions", [])] + [
        f"Duplicate indicator: {bool(c.is_duplicate)}",
        "", f"FINAL RECOMMENDATION: {c.final_decision}", "", "REVIEWER COMMENTS"] + [
        f"- [{r['created_at']}] {r['action']}: {r['comment']}" for r in reviews]
    st.download_button("Download report (.txt)", "\n".join(lines), file_name=f"{cid}_report.txt")

if user["role"] == "admin":
    st.subheader("Data export (admin)")
    for label, sql in [("claims", "SELECT * FROM claims"), ("products", "SELECT * FROM products"),
                       ("warranties", "SELECT * FROM warranties"), ("predictions", "SELECT * FROM predictions"),
                       ("audit_log", "SELECT * FROM audit_log")]:
        data = pd.DataFrame(query(sql)).to_csv(index=False)
        if st.download_button(f"Export {label}.csv", data, file_name=f"{label}.csv", key=label):
            log_action(user["user_id"], "export", label)