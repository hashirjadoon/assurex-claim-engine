import streamlit as st


def require_login(roles=None):
    user = st.session_state.get("user")
    if not user:
        st.warning("Please log in first (Login page).")
        st.stop()
    if roles and user["role"] not in roles:
        st.error("You do not have access to this page.")
        st.stop()
    st.sidebar.write(f"Logged in as **{user['username']}** ({user['role']})")
    if st.sidebar.button("Log out"):
        st.session_state.pop("user")
        st.rerun()
    return user