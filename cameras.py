import streamlit as st
import cv2
import sqlite3

def check_activation(username):
    try:
        conn = sqlite3.connect('apex_security.db')
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM users WHERE username=?", (username,))
        result = cursor.fetchone()
        conn.close()
        if result and result[0] == 'Approved':
            return True
    except:
        pass
    return False

def render_cameras_module():
    st.markdown("## 🌐 APEX Advanced Surveillance Hub")
    st.markdown("---")

    username = st.session_state.get("username", "Operator")

    cam_type = st.selectbox(
        "Select Advanced Feed Source",
        [
            "🔒 Paid LAN / RTSP IP Camera",
            "🎥 HDMI / USB Capture Card",
            "🏛️ Government / Secure Agency Node"
        ]
    )

    if "Paid LAN / RTSP" in cam_type:
        st.markdown("### 🔌 Network Cable (LAN) & IP Camera")
        
        if not check_activation(username):
            st.warning("⚠️ پێویستە ئەکاونتەکەت ئەکتیڤ کرابێت.")
            key = st.text_input("Enter License Key", type="password")
            if st.button("Activate"):
                if key == "APEX-LAN-2026":
                    st.success("✅ ئەکتیڤ کرا!")
                    st.rerun()
                else:
                    st.error("❌ کلیلی هەڵە.")
            return

        rtsp_url = st.text_input("Enter RTSP URL", value="rtsp://admin:@192.168.1.108:554/stream1")
        
        if st.button("Connect LAN Camera"):
            st.success(f"Connecting to {rtsp_url}...")

    elif "HDMI / USB Capture Card" in cam_type:
        st.markdown("### 🎥 External HDMI / USB Capture Card")
        port = st.selectbox("Select Port Index", [1, 2, 3])
        
        if st.button("Initialize Hardware"):
            cap = cv2.VideoCapture(port)
            if cap.isOpened():
                st.success(f"✅ ئامێر لەسەر پۆرت {port} بەسترا!")
                ret, frame = cap.read()
                if ret:
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    st.image(frame, channels="RGB")
                cap.release()
            else:
                st.error(f"❌ هیچ ئامێرێک لەسەر پۆرتی {port} نەدۆزراوەتەوە.")

    elif "Government" in cam_type:
        st.markdown("### 🏛️ Secure Government Node")
        gov_code = st.text_input("Enter Agency Certificate ID", type="password")
        if st.button("Authenticate Agency"):
            if gov_code == "GOV-APEX-999":
                st.success("✅ بڕوانامە پەسەند کرا.")
            else:
                st.error("❌ بڕوانامە هەڵەیە.")