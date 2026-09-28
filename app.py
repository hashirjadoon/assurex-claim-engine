import streamlit as st
from src.db.db_utils import init_db, query

st.set_page_config(page_title="AssureX Claim Engine", page_icon="🛡️", layout="wide")
init_db()

st.title("🛡️ AssureX Claim Engine")
st.write("AI-powered warranty claim validation using a Python classification model, "
         "a Google Teachable Machine image model, and a configurable warranty rule engine.")

user = st.session_state.get("user")
if user:
    st.success(f"Welcome, {user['full_name'] or user['username']} ({user['role']}). Use the sidebar to navigate.")
    notes = query("SELECT message, created_at FROM notifications WHERE user_id=? ORDER BY notification_id DESC LIMIT 5",
                  (user["user_id"],))
    if notes:
        st.subheader("Recent notifications")
        for n in notes:
            st.info(f"{n['created_at']}: {n['message']}")
else:
    st.info("Please log in from the Login page in the sidebar.")