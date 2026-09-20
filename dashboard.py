from typing import Union, Any
import streamlit as st
import cv2
import pandas as pd
import numpy as np
import time

# هاوردەکردنی مۆدیولەکانی APEX
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

try:
    from database import init_db, log_alpr_event, log_face_event

    init_db()
except ImportError:
    log_alpr_event, log_face_event = None, None


@st.cache_resource
def load_ai_engines():
    face_e = KYCEngine() if KYCEngine else None
    alpr_e = ALPREngine() if ALPREngine else None
    return face_e, alpr_e


def _safe_bgr_frame(frame: Any) -> np.ndarray:
    if frame is None:
        return np.zeros((480, 640, 3), dtype=np.uint8)

    arr = np.asarray(frame)
    if arr.size == 0:
        return np.zeros((480, 640, 3), dtype=np.uint8)

    if arr.ndim == 2:
        return cv2.cvtColor(arr, cv2.COLOR_GRAY2BGR)
    if arr.shape[-1] == 1:
        return cv2.cvtColor(arr, cv2.COLOR_GRAY2BGR)
    return arr.astype(np.uint8, copy=False)


def _safe_rgb_frame(frame: Any) -> np.ndarray:
    bgr_frame = _safe_bgr_frame(frame)
    return cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)


def show_dashboard():
    if "is_streaming" not in st.session_state:
        st.session_state.is_streaming = False

    selected_source: Union[int, str] = 0

    # Header Metrics Cards
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

    # Main Grid Layout
    left_main, right_sidebar = st.columns([3.2, 1.2])

    with left_main:
        with st.container(border=True):
            st.markdown("##### 📹 APEX LIVE CAMERA WALL `Grid 2x2`")

            c_src1, c_src2 = st.columns([2.5, 1.2])
            with c_src1:
                cam_type = st.selectbox(
                    "Camera Source",
                    [
                        "Webcam (Local 0)",
                        "External / Capture Card (Index 1)",
                        "RTSP IP Camera",
                    ],
                    label_visibility="collapsed",
                )

            if cam_type == "External / Capture Card (Index 1)":
                selected_source = 1
            elif cam_type == "RTSP IP Camera":
                selected_source = str(
                    st.text_input(
                        "RTSP URL:",
                        value="rtsp://RHKLJ4jf:qR9ERldHfSZdz3aG@192.168.173.110:554/live/ch1",
                    )
                )
            else:
                selected_source = 0

            with c_src2:
                if not st.session_state.is_streaming:
                    if st.button(
                        "▶ Start Stream",
                        use_container_width=True,
                        key="btn_start_stream",
                    ):
                        st.session_state.is_streaming = True
                        st.rerun()
                else:
                    if st.button(
                        "⏹ Stop Stream",
                        type="primary",
                        use_container_width=True,
                        key="btn_stop_stream",
                    ):
                        st.session_state.is_streaming = False
                        st.rerun()

            c1, c2 = st.columns(2)
            with c1:
                st.caption("🔴 CAM-01: Main Entrance (Face ID) • LIVE")
                cam1_place = st.empty()
                st.caption("🔴 CAM-03: Reception • LIVE")
                cam3_place = st.empty()

            with c2:
                st.caption("🔴 CAM-02: Parking Area (ALPR) • LIVE")
                cam2_place = st.empty()
                st.caption("🔴 CAM-04: Restricted Zone • LIVE")
                cam4_place = st.empty()

            placeholder_url = (
                "https://dummyimage.com/600x350/0f172a/38bdf8&text=SIGNAL+STANDBY"
            )
            if not st.session_state.is_streaming:
                cam1_place.image(placeholder_url, use_container_width=True)
                cam2_place.image(placeholder_url, use_container_width=True)
                cam3_place.image(placeholder_url, use_container_width=True)
                cam4_place.image(placeholder_url, use_container_width=True)

    with right_sidebar:
        with st.container(border=True):
            st.markdown("##### 🚨 ACTIVE ALERTS")
            st.error("🔴 **Intrusion Alert**\n\nCAM-04 | Restricted Zone")
            st.warning("⚠ **High Occupancy**\n\nCAM-02 | Parking Area")

        with st.container(border=True):
            st.markdown("##### 🎯 TARGET & ALPR LIVE FEED")
            analysis_box = st.empty()
            analysis_box.info("ℹ️ Monitoring Active - No Threat")

        with st.container(border=True):
            st.markdown("##### 🤖 AI ENGINES")
            st.markdown("🟢 **Face Recognizer:** OPTIMIZED")
            st.markdown("🟢 **ALPR Engine:** OPTIMIZED")

    # High-Performance Streaming Loop
    if st.session_state.is_streaming:
        if CameraStream is None:
            st.error("cameras.py Not Found")
            return

        cam = CameraStream(selected_source)
        face_engine = KYCEngine() if KYCEngine else None
        alpr_engine = ALPREngine() if ALPREngine else None

        frame_count = 0
        detected_targets = []
        detected_plates = []

        while st.session_state.is_streaming:
            frame = cam.get_frame()
            if frame is None:
                time.sleep(0.01)
                continue

            frame_count += 1
            frame_face = _safe_bgr_frame(frame.copy())
            frame_alpr = _safe_bgr_frame(frame.copy())

            # ⚡ پشکنینی AI تەنها لە هەموو ٤ فریم جارێکدا ئەنجام دەدرێت تا کامێراکە خاو نەبێتەوە
            if frame_count % 4 == 0:
                if face_engine and hasattr(face_engine, "process_frame_with_details"):
                    try:
                        processed_face = face_engine.process_frame_with_details(frame_face)
                        if isinstance(processed_face, tuple) and len(processed_face) == 2:
                            frame_face, detected_targets = processed_face
                        else:
                            frame_face = _safe_bgr_frame(processed_face)
                    except Exception:
                        pass

                if alpr_engine and hasattr(alpr_engine, "process_frame"):
                    try:
                        processed_alpr = alpr_engine.process_frame(frame_alpr)
                        if isinstance(processed_alpr, tuple) and len(processed_alpr) == 2:
                            frame_alpr, detected_plates = processed_alpr
                        else:
                            frame_alpr = _safe_bgr_frame(processed_alpr)
                    except Exception:
                        pass

            # 🚀 نیشاندانی ڕاستەوخۆی فیدەکە بە خێرایی بەرز
            rgb_frame = _safe_rgb_frame(frame)
            cam1_place.image(
                (_safe_rgb_frame(frame_face) if frame_count % 4 == 0 else rgb_frame),
                use_container_width=True,
            )
            cam2_place.image(
                (_safe_rgb_frame(frame_alpr) if frame_count % 4 == 0 else rgb_frame),
                use_container_width=True,
            )
            cam3_place.image(rgb_frame, use_container_width=True)
            cam4_place.image(rgb_frame, use_container_width=True)

            # Update Right Analysis Panel
            if detected_targets:
                for target in detected_targets:
                    t_name = str(target.get("name", "Target"))
                    if target.get("status") == "MATCHED":
                        analysis_box.success(
                            f"🎯 **TARGET MATCHED!**\n\n👤 Name: {t_name}"
                        )
            elif detected_plates:
                for plate in detected_plates:
                    p_num = str(plate.get("plate", ""))
                    analysis_box.success(
                        f"🚗 **PLATE DETECTED!**\n\n🔢 Number: {p_num}"
                    )

            time.sleep(0.001)

        cam.release()


if __name__ == "__main__":
    show_dashboard()
