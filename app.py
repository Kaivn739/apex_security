import streamlit as st

# ⚠️ پێویستە ئەم فەرمانە لە هەموو فەرمانەکانی تری Streamlit لەسەرەوەتر بێت[span_2](start_span)[span_2](end_span)
st.set_page_config(
    page_title="APEX Security System",
    page_icon="🛡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

import auth
import dashboard
import style


def main():
    # 1. تێپەڕاندنی دۆخی چوونەژوورەوە
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    # 2. ڕاوتینگی ڕووکارەکان
    if not st.session_state.authenticated:
        auth.login_screen()
    else:
        style.apply_apex_style()
        dashboard.show_dashboard()


if __name__ == "__main__":
    main()
