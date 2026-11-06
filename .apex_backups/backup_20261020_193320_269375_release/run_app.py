import streamlit as st

import style
import auth
import dashboard
import kyc
import admin

st.set_page_config(page_title="APEX Security System", page_icon="🛡️", layout="wide")


if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "username" not in st.session_state:
    st.session_state.username = ""


def main():

    # APEX Style
    if hasattr(style, "apply_custom_style"):
        style.apply_custom_style()

    # Sidebar
    st.sidebar.markdown("## 🛡️ APEX NAVIGATION")

    menu = st.sidebar.selectbox(
        "Select Module", ["Dashboard / Login", "KYC Registration", "Admin Panel"]
    )

    # =========================
    # DASHBOARD / LOGIN
    # =========================

    if menu == "Dashboard / Login":

        if not st.session_state.logged_in:

            if hasattr(auth, "show_auth"):
                auth.show_auth()

            elif hasattr(auth, "render_login"):
                auth.render_login()

            else:
                st.subheader("🔐 APEX User Login")

                username = st.text_input("Username")
                password = st.text_input("Password", type="password")

                if st.button("Login"):

                    if username and password:

                        st.session_state.logged_in = True
                        st.session_state.username = username

                        st.rerun()

                    else:
                        st.warning("Please enter username and password.")

        else:

            st.success(f"Welcome back, {st.session_state.username}!")

            # APEX MAIN DASHBOARD
            if hasattr(dashboard, "show_dashboard"):
                dashboard.show_dashboard()

            elif hasattr(dashboard, "render_dashboard"):
                dashboard.render_dashboard()

            else:
                st.error("Dashboard function was not found.")

            st.sidebar.markdown("---")

            if st.sidebar.button("Logout"):

                st.session_state.logged_in = False
                st.session_state.username = ""

                st.rerun()

    # =========================
    # KYC
    # =========================

    elif menu == "KYC Registration":

        if hasattr(kyc, "show_kyc"):
            kyc.show_kyc()

        elif hasattr(kyc, "render_kyc"):
            kyc.render_kyc()

        else:
            st.error("KYC function was not found.")

    # =========================
    # ADMIN
    # =========================

    elif menu == "Admin Panel":

        if hasattr(admin, "show_admin"):
            admin.show_admin()

        elif hasattr(admin, "render_admin"):
            admin.render_admin()

        else:
            st.error("Admin function was not found.")


if __name__ == "__main__":
    main()
