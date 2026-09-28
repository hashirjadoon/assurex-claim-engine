import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st
from src.auth import require_login
from src.db.db_utils import claim_overview, query, execute, log_action, notify

st.set_page_config(page_title="Claim Status", page_icon="📍", layout="wide")
user = require_login()
st.title("Claim Status Tracking")

STAGES = ["Draft", "Submitted", "Under Evaluation", "Additional Information Required",
          "Manual Review", "Approved", "Rejected", "Closed"]

if user["role"] == "customer":
    rows = claim_overview("c.user_id = ?", (user["user_id"],))
else:
    rows = claim_overview()
if not rows:
    st.info("No claims yet.")
    st.stop()

st.dataframe(pd.DataFrame(rows)[["claim_id", "product_id", "fault_type", "claim_date", "status",
                                 "final_decision", "consistency_status"]], use_container_width=True)

cid = st.selectbox("Open claim", [r["claim_id"] for r in rows])
c = next(r for r in rows if r["claim_id"] == cid)

st.subheader(f"{cid}: {c['status']}")
st.write(" → ".join(f"**{s}**" if s == c["status"] else s for s in STAGES))
st.write(f"Automated recommendation: **{c['final_decision']}** | Python: {c['python_class']} | "
         f"GTM: {c['gtm_class']} | Consistency: {c['consistency_status']} | Rules: {c['rule_status']}")

ex = json.loads(c["explanation_json"] or "{}")
if ex:
    a, b = st.columns(2)
    a.markdown("**Supporting**")
    for s in ex.get("supporting", []):
        a.write(f"✅ {s}")
    b.markdown("**Opposing / contradictions**")
    for s in ex.get("opposing", []) + ex.get("contradictions", []):
        b.write(f"⚠️ {s}")
    if ex.get("additional_evidence_required"):
        st.info("Additional evidence required: " + ", ".join(ex["additional_evidence_required"]))

reviews = query("SELECT r.action, r.comment, r.override_decision, r.created_at, u.username FROM reviews r "
                "LEFT JOIN users u ON u.user_id = r.reviewer_id WHERE r.claim_id = ? ORDER BY r.review_id", (cid,))
if reviews:
    st.markdown("**Reviewer history**")
    st.dataframe(pd.DataFrame(reviews), use_container_width=True)

if c["status"] in ("Approved", "Rejected") and st.button("Close claim"):
    execute("UPDATE claims SET status='Closed' WHERE claim_id=?", (cid,))
    log_action(user["user_id"], "status_change", "claim", cid, "Closed")
    st.rerun()

if c["status"] == "Additional Information Required":
    st.warning("The reviewer requested more information. Submit a new claim with the missing documents.")