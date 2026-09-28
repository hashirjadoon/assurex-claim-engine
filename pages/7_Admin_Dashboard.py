import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st
from src.auth import require_login
from src.db.db_utils import claim_overview, query, log_action

st.set_page_config(page_title="Admin Dashboard", page_icon="📊", layout="wide")
user = require_login(["admin"])
st.title("Administrator Dashboard")

rows = claim_overview()
df = pd.DataFrame(rows)

if df.empty:
    st.info("No claims yet.")
else:
    df["py_top"] = df[["py_conf_valid", "py_conf_invalid", "py_conf_manual"]].max(axis=1)
    df["gtm_top"] = df[["gtm_conf_valid", "gtm_conf_invalid", "gtm_conf_manual"]].max(axis=1)
    m = st.columns(6)
    m[0].metric("Total claims", len(df))
    m[1].metric("Likely valid", int((df.final_decision == "Likely Valid").sum()))
    m[2].metric("Likely invalid", int((df.final_decision == "Likely Invalid").sum()))
    m[3].metric("Manual review", int((df.final_decision == "Manual Review Required").sum()))
    m[4].metric("Pending", int(df.status.isin(["Manual Review", "Additional Information Required"]).sum()))
    m[5].metric("Duplicate alerts", int(df.is_duplicate.sum()))
    n = st.columns(3)
    n[0].metric("Model disagreements", int((df.class_match == 0).sum()))
    n[1].metric("Avg Python confidence", f"{df.py_top.mean():.1%}")
    n[2].metric("Avg GTM confidence", f"{df.gtm_top.mean():.1%}")

    a, b = st.columns(2)
    a.subheader("Claims by decision")
    a.bar_chart(df.final_decision.value_counts())
    b.subheader("Consistency status")
    b.bar_chart(df.consistency_status.value_counts())
    st.subheader("Claim trend")
    st.line_chart(df.assign(day=df.created_at.str[:10]).groupby("day").size())

st.subheader("Monitoring and anomaly alerts")
failed = query("SELECT COUNT(*) AS n FROM audit_log WHERE action='failed_login'")[0]["n"]
alerts = []
if failed >= 3:
    alerts.append(f"{failed} failed login attempts recorded")
if not df.empty:
    if int(df.is_duplicate.sum()) > 0:
        alerts.append(f"{int(df.is_duplicate.sum())} duplicate claim/document alerts")
    if (df.class_match == 0).mean() > 0.3:
        alerts.append("Excessive disagreement between the two models (over 30%)")
    low = int(((df.py_top < 0.55) | (df.gtm_top < 0.55)).sum())
    if low:
        alerts.append(f"{low} low-confidence predictions")
for al in alerts or ["No anomalies detected"]:
    if alerts:
        st.warning(al)
    else:
        st.success(al)

st.subheader("Configurable thresholds")
path = ROOT / "config" / "thresholds.json"
t = json.loads(path.read_text())
c1, c2, c3, c4 = st.columns(4)
t["min_confidence"] = c1.number_input("Minimum confidence", 0.0, 1.0, float(t["min_confidence"]), 0.05)
t["strong_match_max_diff"] = c2.number_input("Strong match max diff", 0.0, 1.0, float(t["strong_match_max_diff"]), 0.05)
t["acceptable_match_max_diff"] = c3.number_input("Acceptable match max diff", 0.0, 1.0, float(t["acceptable_match_max_diff"]), 0.05)
t["expiry_alert_days"] = c4.number_input("Expiry alert days", 1, 365, int(t["expiry_alert_days"]))
if st.button("Save thresholds"):
    path.write_text(json.dumps(t, indent=2))
    log_action(user["user_id"], "update_thresholds", "config", "thresholds.json", json.dumps(t))
    st.success("Saved")

st.subheader("Audit trail (latest 100)")
st.dataframe(pd.DataFrame(query("SELECT * FROM audit_log ORDER BY log_id DESC LIMIT 100")), use_container_width=True)