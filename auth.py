import streamlit as st
import sqlite3
import style  # بانگکردنی فایلی ستایل بە جیا

def render_login():
    # بەکارهێنانی ستایلی تایبەت لە فایلی style.py
    if hasattr(style, 'apply_style'):
        style.apply_style()

    # هەڵبژاردنی زمان لە باڕی لاوەکی
    lang = st.sidebar.selectbox("Select Language / زمان", ["English", "کوردی"])

    # دروستکردنی شاشەی لۆگین لە ناوەڕاست (Centered Layout)
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        
        if lang == "کوردی":
            st.markdown("<h1 style='text-align: center; color: #FF0033;'>🛡️ ئایپیکس</h1>", unsafe_allow_html=True)
            st.markdown("<h4 style='text-align: center; color: #A0A0A0;'>پەناگەی چوونەژووری ئەمنی</h4><br>", unsafe_allow_html=True)
        else:
            st.markdown("<h1 style='text-align: center; color: #FF0033;'>🛡️ APEX</h1>", unsafe_allow_html=True)
            st.markdown("<h4 style='text-align: center; color: #A0A0A0;'>SECURE ACCESS CONSOLE</h4><br>", unsafe_allow_html=True)

        # بەکارهێنانی st.form بۆ ئەوەی کلیلی Enter کار بکات لە کاتی لۆگیندا
        with st.form("login_form"):
            if lang == "کوردی":
                login_username = st.text_input("ناوی بەکارهێنەر (Username)")
                login_passcode = st.text_input("کۆدی نهێنی (Password)", type="password")
                submit_btn = st.form_submit_button("چوونەژوورەوە (Login / Enter)")
            else:
                login_username = st.text_input("OPERATOR USERNAME")
                login_passcode = st.text_input("SECURITY ACCESS CODE", type="password")
                submit_btn = st.form_submit_button("INITIALIZE CONSOLE (Enter)")

            if submit_btn:
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
                        st.session_state.username = login_username
                        st.success("✅ سەرکەوتوو بوو! دەگوازرێیتەوە...")
                        st.rerun()
                    else:
                        st.error("❌ ڕەتکرایەوە! زانیارییەکان هەڵەن یان هێشتا پەسەند نەکراوە.")

        st.markdown("<br>", unsafe_allow_html=True)