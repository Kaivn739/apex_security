import streamlit as st
import sqlite3
import random
import string
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from style import apply_apex_style

def send_email_to_user(receiver_email, username, access_code):
    # لێرە زانیاری ئیمەیڵی بەڕێوەبەرت دانێ (Gmail App Password پێویستە)
    sender_email = "123shex123@gmail.com"
    sender_password = "mkbf mcbh pycu uxqh"
    
    subject = "🛡 APEX Security - Secure Access Code"
    body = f"""
    Hello {username},
    
    Your KYC application for APEX Security Console has been APPROVED.
    Your one-time secure access code is: {access_code}
    
    Keep this code confidential. It is required for your initial login.
    
    Best regards,
    APEX Security Team
    """
    
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))
    
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, receiver_email, message.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def show_admin():
    apply_apex_style()
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align: center; color: #FF0033;'>🛡 APEX ADMIN</h1>", unsafe_allow_html=True)
        st.markdown("<h4 style='text-align: center; color: #A0A0A0;'>SECURE MANAGEMENT CONSOLE</h4><br>", unsafe_allow_html=True)
        
        admin_pass = st.text_input("ADMIN ACCESS PASSWORD", type="password", placeholder="Enter admin password...")
        
        if admin_pass == "123":
            st.success("✅ دەسەڵاتی بەڕێوەبەر چالاک کرا.")
            st.markdown("---")
            st.subheader("📋 داواکارییە چاوەڕوانکراوەکانی KYC")
            
            conn = sqlite3.connect('apex_security.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT,
                    email TEXT,
                    phone TEXT,
                    address TEXT,
                    access_code TEXT,
                    status TEXT
                )
            ''')
            conn.commit()
            
            cursor.execute("SELECT id, username, email, phone, address FROM users WHERE status='Pending'")
            pending_users = cursor.fetchall()
            
            if not pending_users:
                st.info("هیچ داواکارییەکی چاوەڕوانکراو نییە.")
            else:
                for p in pending_users:
                    st.markdown(f"""
                        <div style="background-color: #120505; padding: 15px; border-radius: 8px; border: 1px solid #8B0000; margin-bottom: 10px;">
                            <b>ID:</b> {p[0]}<br>
                            <b>Username/Name:</b> {p[1]}<br>
                            <b>Email:</b> {p[2]}<br>
                            <b>Phone:</b> {p[3]}<br>
                            <b>Address:</b> {p[4]}
                        </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button(f"Approve & Email Code to {p[1]}", key=f"approve_btn_{p[0]}"):
                        # دروستکردنی کۆدێکی نهێنی پۆلێنی
                        generated_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                        
                        # ناردنی کۆدەکە بۆ ئیمەیڵی بەکارهێنەر