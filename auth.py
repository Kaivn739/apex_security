import streamlit as st
import sqlite3
from style import apply_apex_style

def show_auth():
    apply_apex_style()
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align: center; color: #FF0033;'>🛡️ APEX</h1>", unsafe_allow_html=True)
        st.markdown("<h4 style='text-align: center; color: #A0A0A0;'>SECURE ACCESS CONSOLE</h4><br>", unsafe_allow_html=True)
        
        st.markdown("### AUTHORIZE SESSION")
        login_username = st.text_input("OPERATOR USERNAME", placeholder="Enter your name...", key="l_user")
        login_passcode = st.text_input("SECURITY ACCESS CODE", type="password", placeholder="Enter your code...", key="l_pass")
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("INITIALIZE CONSOLE"):
            if not login_username or not login_passcode:
                st.warning("⚠️ تکایە هەردوو خانەکە پڕ بکەرەوە!")
            else:
                conn = sqlite3.connect('apex_security.db')
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE username=? AND access_code=? AND status='Approved'", 
                               (login_username, login_passcode))
                user = cursor.fetchone()
                conn.close()
                
                if user:
                    st.session_state.logged_in = True
                    st.session_state.operator = login_username
                    st.success("✅ سەرکەوتوو بوو! دەگوازرێیتەوە...")
                    st.rerun()
                else:
                    st.error("❌ ڕەتکرایەوە! یان زانیارییەکان هەڵەن، یان هێشتا KYCـیەکەت پەسەند نەکراوە.")