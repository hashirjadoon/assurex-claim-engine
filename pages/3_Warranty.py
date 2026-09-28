import json
import sys
from datetime import date, timedelta
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st
from src.auth import require_login
from src.db.db_utils import query, execute, log_action

st.set_page_config(page_title="Warranties", page_icon="🗂️", layout="wide")
user = require_login()
st.title("Warranty Records")

alert_days = json.loads((ROOT / "config" / "thresholds.json").read_text()).get("expiry_alert_days", 30)
rows = query(
    "SELECT p.product_id, p.product_name, p.category, p.serial_number, w.warranty_type, w.provider, "
    "w.start_date, w.expiry_date FROM products p JOIN warranties w ON w.product_id = p.product_id "
    "WHERE (p.user_id = ? OR ? != 'customer')", (user["user_id"], user["role"]))

if not rows:
    st.info("No warranties yet. Register a product first.")
    st.stop()

today = date.today()
for r in rows:
    left = (date.fromisoformat(r["expiry_date"]) - today).days
    r["days_remaining"] = left
    r["status"] = "Expired" if left < 0 else ("Nearing Expiry" if left <= alert_days else "Active")
    if r["warranty_type"] == "extended" and left >= 0:
        r["status"] += " (Extended)"

df = pd.DataFrame(rows)
f = st.selectbox("Filter", ["All", "Active", "Nearing Expiry", "Expired"])
view = df if f == "All" else df[df["status"].str.startswith(f)]
st.dataframe(view, use_container_width=True)

for r in rows:
    if r["status"].startswith("Nearing"):
        st.warning(f"{r['product_name']} ({r['product_id']}) warranty expires in {r['days_remaining']} days")

st.subheader("Add extended warranty")
prods = {f"{r['product_id']} - {r['product_name']}": r for r in rows if r["warranty_type"] == "standard"}
if prods:
    choice = prods[st.selectbox("Product", list(prods))]
    days = st.selectbox("Extended duration (days)", [180, 365, 730])
    provider = st.text_input("Extended warranty provider", value="Extended Care Ltd")
    if st.button("Add extended warranty"):
        start = date.fromisoformat(choice["expiry_date"])
        execute("INSERT INTO warranties (product_id, warranty_type, provider, start_date, duration_days, expiry_date) "
                "VALUES (?,?,?,?,?,?)",
                (choice["product_id"], "extended", provider, start.isoformat(), days,
                 (start + timedelta(days=days)).isoformat()))
        log_action(user["user_id"], "add_extended_warranty", "product", choice["product_id"])
        st.success("Extended warranty added")
        st.rerun()