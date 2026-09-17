from typing import Union
import streamlit as st
import cv2
import pandas as pd
import numpy as np
import time

# هاوردەکردنی مۆدیولەکانی APEX بە شێوازی سەلامەت
try:
    from cameras import CameraStream
except ImportError:
    CameraStream = None

try:
    from face_recognizer import FaceRecognizerEngine as KYCEngine
except ImportError:
    KYCEngine = None

try:
    from alpr_engine import ALPREngine
except ImportError:
    ALPREngine = None

try:
    from alerts import send_target_telegram_alert
except ImportError:
    send_target_telegram_alert = None


def show_dashboard():
    if 'is_streaming' not in st.session_state:
        st.session_state.is_streaming = False

    selected_source: Union[int, str] = 0

    # 1. Header Metrics Cards
    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        with st.container(border=True):
            st.caption("CAMERAS")
            st.subheader("24")
            st.caption("🟢 22 Online / 🔴 2 Offline")
    with m2:
        with st.container(border=True):
            st.caption("PEOPLE DETECTED")
            st.subheader("128")
            st.caption("Currently Active")
    with m3:
        with st.container(border=True):
            st.caption("TODAY ENTRIES")
            st.subheader("74")
            st.caption("Today's Entries")
    with m4:
        with st.container(border=True):
            st.caption("TODAY EXITS")
            st.subheader("61")
            st.caption("Today's Exits")
    with m5:
        with st.container(border=True):
            st.caption("OCCUPANCY")
            st.subheader("68%")
            st.caption("Average Zones")

    # 2. Main Middle Section Layout (Grid 2x2 + Side Alerts & Target Panel)
    left_main, right_sidebar = st.columns([3.2, 1.2])

    with left_main:
        with st.container(border=True):
            st.markdown("##### 📹 LIVE CAMERA WALL Grid 2x2")

            c_src1, c_src2 = st.columns([2.5, 1.2])
            with c_src1:
                cam_type = st.selectbox(
                    "Camera Source",
                    ["Webcam (Local 0)", "External / Capture Card (Index 1)", "RTSP IP Camera"],
                    label_visibility="collapsed"
                )

            if cam_type == "External / Capture Card (Index 1)":
                selected_source = 1
            elif cam_type == "RTSP IP Camera":
                rtsp_input = st.text_input(
                    "RTSP URL:",
                    value="rtsp://RHKLJ4jf:qR9ERldHfSZdz3aG@192.168.173.110:554/live/ch1"
                )
                selected_source = rtsp_input
            else:
                selected_source = 0

            with c_src2:
                if not st.session_state.is_streaming:
                    if st.button("▶ Start Stream", use_container_width=True, key="btn_start"):
                        st.session_state.is_streaming = True
                        st.rerun()
                else:
                    if st.button("⏹ Stop Stream", type="primary", use_container_width=True, key="btn_stop"):
                        st.session_state.is_streaming = False
                        st.rerun()
            # Grid 2x2 Placeholders
            c1, c2 = st.columns(2)
            with c1:
                st.caption("🔴 CAM-01: Main Entrance • LIVE")
                cam1_place = st.empty()
                st.caption("🔴 CAM-03: Reception • LIVE")
                cam3_place = st.empty()

            with c2:
                st.caption("🔴 CAM-02: Parking Area (ALPR) • LIVE")
                cam2_place = st.empty()
                st.caption("🔴 CAM-04: Restricted Zone • LIVE")
                cam4_place = st.empty()
            with c2:
                st.caption("🔴 CAM-02: Parking Area (ALPR) • LIVE")
                cam2_place = st.empty()
                st.caption("🔴 CAM-04: Restricted Zone • LIVE")
                cam4_place = st.empty()

            placeholder_url = "https://dummyimage.com/600x350/0f172a/38bdf8&text=SIGNAL+STANDBY"
            if not st.session_state.is_streaming:
                cam1_place.image(placeholder_url, use_container_width=True)
                cam2_place.image(placeholder_url, use_container_width=True)
                cam3_place.image(placeholder_url, use_container_width=True)
                cam4_place.image(placeholder_url, use_container_width=True)
