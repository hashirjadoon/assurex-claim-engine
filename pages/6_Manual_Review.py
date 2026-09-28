import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st
from src.auth import require_login
from src.db.db_utils import claim_overview, query, execute, log_action, notify


st.set_page_config(page_title="Manual Review", page_icon="🔎", layout="wide")
user = require_login(["reviewer", "admin"])
st.title("Manual Review Queue")

queue = claim_overview("c.status = 'Manual Review'")
st.write(f"{len(queue)} claim(s) waiting")
if not queue:
    st.stop()

st.dataframe(pd.DataFrame(queue)[["claim_id", "fault_type", "claim_date", "python_class", "gtm_class",
                                  "consistency_status", "rule_status"]], use_container_width=True)

cid = st.selectbox("Select claim", [q["claim_id"] for q in queue])
c = next(q for q in queue if q["claim_id"] == cid)

l, r = st.columns([2, 1])
with l:
    st.write(f"**Fault:** {c['fault_type']}  |  **Description:** {c['fault_description']}")
    st.write(f"**Original AI recommendation:** {c['final_decision']} (preserved in audit history)")
    st.dataframe(pd.DataFrame({
        "Python": [c["py_conf_valid"], c["py_conf_invalid"], c["py_conf_manual"]],
        "GTM": [c["gtm_conf_valid"], c["gtm_conf_invalid"], c["gtm_conf_manual"]]},
        index=["Valid", "Invalid", "ManualReview"]).style.format("{:.1%}"))
    ex = json.loads(c["explanation_json"] or "{}")
    for s in ex.get("opposing", []) + ex.get("contradictions", []):
        st.write("⚠️", s)
    docs = query("SELECT doc_type, filename, file_path FROM documents WHERE claim_id=?", (cid,))
    for d in docs:
        if d["file_path"].lower().endswith((".png", ".jpg", ".jpeg")):
            st.image(d["file_path"], caption=d["doc_type"], width=250)
        else:
            st.write(f"{d['doc_type']}: {d['filename']}")
with r:
    if c["card_path"]:
        st.image(c["card_path"], caption="Claim Summary Card", width=250)

st.subheader("Reviewer decision")
action = st.radio("Action", ["Approve", "Reject", "Request additional information"])
comment = st.text_area("Comment / reason (required)")
if st.button("Submit decision", type="primary"):
    if not comment.strip():
        st.error("A comment is required")
    else:
        new_status = {"Approve": "Approved", "Reject": "Rejected",
                      "Request additional information": "Additional Information Required"}[action]
        override = new_status if new_status in ("Approved", "Rejected") else None
        execute("INSERT INTO reviews (claim_id, reviewer_id, action, comment, override_decision) VALUES (?,?,?,?,?)",
                (cid, user["user_id"], action, comment.strip(), override))
        execute("UPDATE claims SET status=? WHERE claim_id=?", (new_status, cid))
        log_action(user["user_id"], "reviewer_action", "claim", cid,
                   f"{action} | original AI: {c['final_decision']} | reason: {comment.strip()}")
        owner = query("SELECT user_id FROM claims WHERE claim_id=?", (cid,))[0]["user_id"]
        notify(owner, f"Claim {cid} review completed: {new_status}")
        st.success(f"Claim {cid} set to {new_status}")
        st.rerun()