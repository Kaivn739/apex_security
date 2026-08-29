import streamlit as st

# ڕێکخستنی سەرەتایی پەڕە
st.set_page_config(
    page_title="APEX Security System",
    page_icon="🛡",
    layout="wide"
)

def main():
    # دیزاینی ستایلی سەرەکی
    st.markdown("""
        <style>
        .main-title {
            text-align: center;
            color: #ff4b4b;
            font-family: sans-serif;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<h1 class='main-title'>🛡 APEX SECURITY SYSTEM</h1>", unsafe_allow_html=True)
    st.write("---")

    # سیستەمی کۆنتڕۆڵی لاوەکی بۆ هەرسێ بەشەکە
    menu = st.sidebar.selectbox("Navigation", ["Login", "Register / KYC", "Admin Console"])

    if menu == "Login":
        st.subheader("🔐 User Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        if st.button("Login"):
            if username and password:
                st.success(f"Welcome back, {username}!")
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
                st.success("Registration & KYC data submitted successfully!")
            else:
                st.warning("Please fill in the required fields.")

    elif menu == "Admin Console":
        st.subheader("🛡 APEX ADMIN CONSOLE")
        admin_pass = st.text_input("Enter Admin Password", type="password")
        
        if admin_pass == "123":
            st.success("Access Granted to Admin Panel!")
            st.info("System logs and security configurations are active.")
        elif admin_pass:
            st.error("Incorrect Admin Password!")

if __name__ == "__main__":
    main()