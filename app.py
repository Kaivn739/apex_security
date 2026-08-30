import streamlit as st

# بانگێشتکردنی فایلە دەرەکییەکان بە پێی ئەرکی خۆیان
import style
import auth
import dashboard
import admin
import kyc

# ڕێکخستنی سەرەتایی پەڕە
st.set_page_config(
    page_title="APEX Security System",
    page_icon="🛡",
    layout="wide"
)

def main():
    # ۱. جێبەجێکردنی ستایلی تایبەت لە فایلی style.py
    if hasattr(style, 'apply_style'):
        style.apply_style()

    # ۲. کۆنتڕۆڵکردنی دۆخی چوونەژوورەوە لە Session State
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'username' not in st.session_state:
        st.session_state.username = ""

    # ۳. سیستەمی هاتوچۆ بۆ ئەو کەسانەی هێشتا لۆگینیان نەکردووە
    if not st.session_state.logged_in:
        st.sidebar.markdown("### 🛡 APEX Navigation")
        choice = st.sidebar.selectbox("Select Module", ["Login", "Register / KYC", "Admin Console"])

        if choice == "Login":
            # بانگکردنی بەشی لۆگین لە فایلی auth.py یان home.py
            if hasattr(auth, 'render_login'):
                auth.render_login()
            else:
                st.subheader("🔐 User Login Portal")
                u = st.text_input("Username")
                p = st.text_input("Password", type="password")
                if st.button("Login"):
                    if u and p:
                        st.session_state.logged_in = True
                        st.session_state.username = u
                        st.rerun()
                    else:
                        st.warning("Please fill in all fields.")

        elif choice == "Register / KYC":
            kyc.render_kyc()

        elif choice == "Admin Console":
            # بانگکردنی بەشی ئەدمن لە فایلی admin.py
            if hasattr(admin, 'render_admin'):
                admin.render_admin()
            else:
                st.subheader("🛡 Admin Security Gateway")
                ap = st.text_input("Admin Key", type="password")
                if ap == "123":
                    st.session_state.logged_in = True
                    st.session_state.username = "Admin"
                    st.rerun()

    else:
        # ٤. کاتێک بەکارهێنەر لۆگین دەکات، داشبۆردی سەرەکی لە dashboard.py کار دەکات
        if hasattr(dashboard, 'render_dashboard'):
            dashboard.render_dashboard()
        else:
            st.sidebar.success(f"Active User: {st.session_state.username}")
            if st.sidebar.button("Logout"):
                st.session_state.logged_in = False
                st.session_state.username = ""
                st.rerun()

            st.title(f"🚀 APEX Central Dashboard - Welcome {st.session_state.username}")
            st.write("---")
            st.success("All modular files are successfully coordinated through app.py!")

if __name__ == "__main__":
    main()