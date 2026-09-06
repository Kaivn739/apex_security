import streamlit as st
import sqlite3

def check_credentials(username, password):
    """پشکنینی ناوی بەکارهێنەر و تێپەڕەوشە لە داتا بەیسدا"""
    conn = sqlite3.connect("apex_security.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
    user = cursor.fetchone()
    
    conn.close()
    return user

def login_screen():
    """ڕووکاری چوونەژوورەوەی سیستم"""
    st.subheader("🔐 چوونەژوورەوە بۆ سیستمی ئەپێکس (Apex Security)")
    
    with st.form("login_form"):
        username = st.text_input("ناوی بەکارهێنەر (Username)")
        password = st.text_input("تێپەڕەوشە (Password)", type="password")
        submit_button = st.form_submit_button("چوونەژوورەوە")
        
        if submit_button:
            user = check_credentials(username, password)
            if user:
                st.session_state["authenticated"] = True
                st.session_state["username"] = username
                st.session_state["role"] = user[3] # پلەی بەکارهێنەر
                st.success(f"بەخێر بێیتەوە، {username}!")
                st.rerun()
            else:
                st.error("ناوی بەکارهێنەر یان تێپەڕەوشە هەڵەیە!")

def require_auth():
    """پشکنین بۆ دڵنیابوون لەوەی ئایا بەکارهێنەر چۆتە ژوورەوە یان نا"""
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
        
    if not st.session_state["authenticated"]:
        login_screen()
        return False
    return True