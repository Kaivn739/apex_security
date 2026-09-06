import streamlit as st
import cv2
import pandas as pd
import numpy as np
from cameras import CameraStream
from kyc_engine import KYCEngine

def show_dashboard():
    # 1. Header Metrics (ئامارەکانی سەرەوەی شاشەکە)
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("CAMERAS", "24", "22 Online / 2 Offline")
    m2.metric("PEOPLE", "128", "Currently Detected")
    m3.metric("ENTRIES", "74", "Today's Entries")
    m4.metric("EXITS", "61", "Today's Exits")
    m5.metric("OCCUPANCY", "68%", "Average Zones")

    st.divider()

    # 2. Main Middle Section: Center (Cameras) & Right Sidebar (Alerts & Status)
    left_main, right_sidebar = st.columns([3, 1])

    with left_main:
        st.markdown("### 📹 LIVE CAMERA WALL Grid 2x2")
        
        # هەڵبژاردنی سەرچاوەی کامێراکان بە ستایلی زۆر بچووک
        cam_src_col1, cam_src_col2 = st.columns([2, 1])
        with cam_src_col1:
            cam_type = st.selectbox(
                "سەرچاوەی کامێرا (Camera Source):",
                ["Webcam (Local 0)", "External / Capture Card (Index 1)", "RTSP IP Camera"],
                label_visibility="collapsed"
            )
        with cam_src_col2:
            run_camera = st.checkbox("داگیرساندنی پەخش (Live Stream)", value=False)

        selected_source = 0
        if cam_type == "External / Capture Card (Index 1)":
            selected_source = 1
        elif cam_type == "RTSP IP Camera":
            selected_source = st.text_input("RTSP URL:", value="rtsp://admin:12345@192.168.1.100:554/stream1")

        # 2x2 Camera Grid
        c1, c2 = st.columns(2)
        with c1:
            st.caption("🔴 CAM-01: Main Entrance • LIVE")
            cam1_place = st.empty()
            st.caption("🔴 CAM-03: Reception • LIVE")
            cam3_place = st.empty()

        with c2:
            st.caption("🔴 CAM-02: Parking Area • LIVE")
            cam2_place = st.empty()
            st.caption("🔴 CAM-04: Restricted Zone • LIVE")
            cam4_place = st.empty()

        # Camera Control Toolbar (دوگمەکانی خوار کامێراکان وەک دیزاینەکە)
        st.caption("⚙️ Camera Toolbar: 🎛️ Grid 2x2 | 🎙️ Mute | 🔴 Record | ⚙️ Settings")

    with right_sidebar:
        # ACTIVE ALERTS
        st.markdown("### 🚨 ACTIVE ALERTS")
        st.error("🔴 Intrusion Detected\n\nCAM-04 | Restricted Zone - 18:52:15")
        st.error("🔥 Fire Detection Alert\n\nCAM-03 | Reception - 18:50:41")
        st.warning("⚠️ High Occupancy\n\nCAM-02 | Parking Area")
        st.info("ℹ️ Camera Restored\n\nCAM-01 | Main Entrance")

        st.divider()

        # QUICK ANALYTICS
        st.markdown("### 📊 QUICK ANALYTICS")
        st.progress(0.68, text="Zone Occupancy: 68%")
        st.caption("🟢 Normal: 68%  |  🟠 High: 22%  |  🔴 Critical: 10%")

        st.divider()

        # AI ENGINE STATUS
        st.markdown("### 🤖 AI ENGINE STATUS")
        st.markdown("🟢 Object Detection: ONLINE")
        st.markdown("🟢 Object Tracking: ONLINE")
        st.markdown("🟢 Zone Analytics: ONLINE")
        st.markdown("🟢 Event Manager: ONLINE")

    st.divider()

    # 3. Bottom Dashboard (پێنج ستوونی خوارەوە بەپێی وێنەکە)
    b1, b2, b3, b4, b5 = st.columns(5)

    with b1:
        st.markdown("##### 💻 SYSTEM HEALTH")
        st.caption("CPU Usage: 23%")
        st.progress(0.23)
        st.caption("RAM Usage: 41%")
        st.progress(0.41)
        st.caption("Disk Usage: 82%")
        st.progress(0.82)

    with b2:
        st.markdown("##### 🏛️ ZONE OCCUPANCY")
        st.caption("Main Entrance: 68%")
        st.progress(0.68)
        st.caption("Parking Area: 42%")
        st.progress(0.42)
        st.caption("Restricted Zone: 82%")
        st.progress(0.82)

    with b3:
        st.markdown("##### 📈 ENTRY / EXIT TREND")
        chart_data = pd.DataFrame(
            np.random.randint(10, 40, size=(12, 2)),
            columns=['Entries', 'Exits']
        )
        st.line_chart(chart_data)