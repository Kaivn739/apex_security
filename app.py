import streamlit as st

# ڕێکخستنی سەرەتایی پەڕە
st.set_page_config(
    page_title="APEX Security System",
    page_icon="🛡",
    layout="wide"
)

def main():
    # بەکارهێنانی Session State بۆ کۆنتڕۆڵکردنی دۆخی لۆگین
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'username' not in st.session_state:
        st.session_state.username = ""

    # ئەگەر لۆگینی نەکردبوو، ئەم مۆنیۆیە نیشان بدە
    if not st.session_state.logged_in:
        st.sidebar.markdown("### 🛡 APEX Navigation")
        menu = st.sidebar.selectbox("Choose Action", ["Login", "Register / KYC", "Admin Console"])

        if menu == "Login":
            st.subheader("🔐 User Login")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            
            if st.button("Login"):
                if username and password:
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.success(f"Welcome back, {username}!")
                    st.rerun() # نوێکردنەوەی پەڕەکە بۆ چوونە ژوورەوە
                else:
                    st.warning("Please enter both username and password.")

        elif menu == "Register / KYC":
            st.subheader("📝 New User Registration & KYC")
            reg_username = st.text_input("Choose Username")
            reg_email = st.text_input("Email Address")
            reg_password = st.text_input("Choose Password", type="password")
            kyc_info = st.text_area("KYC Details / Security Notes")
            
            if st.button("Submit Registration"):
                if reg_username and reg_password:
                    st.success("Registration & KYC data submitted successfully! Please go to Login.")
                else:
                    st.warning("Please fill in the required fields.")

        elif menu == "Admin Console":
            st.subheader("🛡 APEX ADMIN CONSOLE")
            admin_pass = st.text_input("Enter Admin Password", type="password")
            
            if admin_pass == "123":
                st.session_state.logged_in = True
                st.session_state.username = "Admin"
                st.success("Access Granted to Admin Panel!")
                st.rerun()
            elif admin_pass:
                st.error("Incorrect Admin Password!")

    else:
        # کاتێک بەکارهێنەر لۆگینی کرد یان سەرکەوتووبوو، ئەم داشبۆردەی نیشان دەدەین
        st.sidebar.success(f"Logged in as: {st.session_state.username}")
        if st.sidebar.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.rerun()

        st.title(f"🚀 Welcome to APEX Dashboard, {st.session_state.username}")
        st.write("---")
        st.info("You are now inside the secure system area. All operational features are active.")
        
        # لێرە دەتوانیت تایبەتمەندییەکانی پڕۆژەکەت (وەک ڕوکاری دوربین، لۆگەکانیش، یان داتای تر) دابنێیت
        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="System Status", value="SECURE", delta="Normal")
        with col2:
            st.metric(label="Active Connections", value="1 LAN Camera", delta="Online")

if name == "main":
    main()