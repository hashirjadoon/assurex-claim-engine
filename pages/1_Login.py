import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
from src.db.db_utils import init_db, create_user, verify_user, log_action

st.set_page_config(page_title="Login", page_icon="🔐")
init_db()
st.title("Login / Register")

tab1, tab2 = st.tabs(["Login", "Register"])
with tab1:
    u = st.text_input("Username", key="lu")
    p = st.text_input("Password", type="password", key="lp")
    if st.button("Log in"):
        user = verify_user(u, p)
        if user:
            st.session_state["user"] = user
            log_action(user["user_id"], "login", "user", str(user["user_id"]))
            st.success(f"Logged in as {user['username']} ({user['role']})")
        else:
            log_action(None, "failed_login", "user", u)
            st.error("Invalid username or password")

with tab2:
    ru = st.text_input("Username", key="ru")
    rn = st.text_input("Full name")
    re_ = st.text_input("Email")
    rp = st.text_input("Password", type="password", key="rp")
    rr = st.selectbox("Role", ["customer", "service_employee"])
    if st.button("Register"):
        if not ru or len(rp) < 6:
            st.error("Username required and password must be at least 6 characters")
        elif create_user(ru, rp, rr, rn, re_):
            st.success("Registered. You can log in now.")
        else:
            st.error("Username already exists")