from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="APEX Security — for Safe, for Ever",
    page_icon="🐉",
    layout="wide",
    initial_sidebar_state="expanded",
)

import auth
import dashboard
import style


def main() -> None:
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        auth.login_screen()
    else:
        style.apply_custom_style()
        dashboard.show_dashboard()


if __name__ == "__main__":
    main()
