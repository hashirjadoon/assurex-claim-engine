import sys
import uuid
from datetime import date, timedelta
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
from src.auth import require_login
from src.db.db_utils import query, execute, log_action

st.set_page_config(page_title="Register Product", page_icon="📦")
user = require_login()
st.title("Register a Product and Warranty")

with st.form("product_form"):
    c1, c2 = st.columns(2)
    name = c1.text_input("Product name")
    category = c2.selectbox("Category", ["Electronics", "Appliances", "Furniture"])
    brand = c1.text_input("Brand")
    model = c2.text_input("Model number")
    serial = c1.text_input("Serial number")
    retailer = c2.text_input("Retailer")
    purchase_date = c1.date_input("Purchase date", value=date.today() - timedelta(days=30))
    price = c2.number_input("Purchase price", min_value=0.0, value=100.0)
    duration = c1.selectbox("Warranty duration (days)", [365, 730, 1095])
    provider = c2.text_input("Warranty provider", value=brand or "Manufacturer")
    submitted = st.form_submit_button("Register")

if submitted:
    if not name or not serial:
        st.error("Product name and serial number are required")
    elif query("SELECT 1 FROM products WHERE serial_number=?", (serial,)):
        st.error("This serial number is already registered")
    else:
        pid = f"PRD-A{uuid.uuid4().hex[:6].upper()}"
        execute("INSERT INTO products (product_id, user_id, product_name, category, brand, model_number, "
                "serial_number, purchase_date, purchase_price, retailer) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (pid, user["user_id"], name, category, brand, model, serial,
                 purchase_date.isoformat(), price, retailer))
        expiry = purchase_date + timedelta(days=int(duration))
        execute("INSERT INTO warranties (product_id, provider, start_date, duration_days, expiry_date) "
                "VALUES (?,?,?,?,?)", (pid, provider, purchase_date.isoformat(), int(duration), expiry.isoformat()))
        log_action(user["user_id"], "register_product", "product", pid)
        st.success(f"Registered {pid}. Warranty expires {expiry.isoformat()}")