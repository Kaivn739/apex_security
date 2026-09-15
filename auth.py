import streamlit as st
import style


def login_screen():
    # 1. سەپاندنی ستایلی شووشەیی لۆگین
    style.apply_dragon_login_style()

    # 2. ڕێکخستنی کانتێنەرەکە لە ناوەڕاستدا
    _, col2, _ = st.columns([1, 2.2, 1])

    with col2:
        with st.form("dragon_login_form"):
            st.markdown(
                "<h1 class='apex-title'>🛡 APEX SECURITY</h1>",
                unsafe_allow_html=True,
            )
            st.markdown(
                "<p style='text-align: center; color: #cbd5e1; font-size: 13px;'>Welcome to the APEX Security System</p>",
                unsafe_allow_html=True,
            )

            username = st.text_input(
                "Username", placeholder="Enter username...", key="login_user"
            )
            password = st.text_input(
                "Password",
                type="password",
                placeholder="Enter password...",
                key="login_pass",
            )

            submit = st.form_submit_button("LOGIN", use_container_width=True)

            if submit:
                username = username.strip()
                password = password.strip()

                if username == "admin" and password in ["1234", "admin"]:
                    st.session_state.authenticated = True
                    st.success("Access Granted!")
                    st.rerun()
                else:
                    st.error("Invalid Username or Password.")