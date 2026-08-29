import streamlit as st

# ڕێکخستنی سەرەتایی پەڕە
st.set_page_config(
    page_title="APEX Security System",
    page_icon="🛡",
    layout="wide"
)

def main():
    # دیزاینی ستایلی سەرەکی و تایتڵ
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

    # سیستەمی کۆنتڕۆڵی لاوەکی بۆ گۆڕینی بەشەکان بە بێ کێشە
    menu = st.sidebar.selectbox("Navigation", ["Home / Login", "Admin Console"])

    if menu == "Home / Login":
        st.subheader("🔐 User Authentication & KYC")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        if st.button("Login"):
            if username and password:
                st.success(f"Welcome back, {username}!")
            else:
                st.warning("Please enter both username and password.")

    elif menu == "Admin Console":
        st.subheader("🛡 APEX ADMIN CONSOLE")
        admin_pass = st.text_input("Enter Admin Password", type="password")
        
        if admin_pass == "123":
            st.success("Access Granted to Admin Panel!")
            # لێرە کۆدی بەشی ئەدمن یان داتابەیسەکەت دادەنێی
            st.info("System logs and security configurations are active.")
        elif admin_pass:
            st.error("Incorrect Admin Password!")

if __name__ == "__main__":
    main()