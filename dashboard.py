import cv2
import streamlit as st
import time

from apex_dashboard_bridge import render_compact_developer_widget
from tier_guard import (
    ALL_DASHBOARD_MODULES,
    render_sidebar_tier_status,
    enforce_camera_limit,
    enforce_ai_permissions,
    render_locked_or_upgrade_view,
)
from apex_vms_optimizer import (
    APEXCameraWatchdog,
    APEXStorageGuard,
    APEXSmartAISampler,
    APEXCameraWatchdog,
)


def show_dashboard():
    render_compact_developer_widget()
    st.markdown("---")
    user_profile = render_sidebar_tier_status()
    allowed_mods = user_profile["tier_info"]["allowed_modules"]
    menu_options = [
        m if m in allowed_mods else f"🔒 {m}" for m in ALL_DASHBOARD_MODULES
    ]
    view_mode = st.sidebar.radio("بەشی کارکردن هەڵبژێرە:", menu_options)
    if render_locked_or_upgrade_view(view_mode):
        return
    if "camera_config" not in st.session_state:

        st.session_state.camera_config = {
            1: {
                "name": "cam-01 - Main Gate",
                "type": "LAN Cable (IP)",
                "source": "192.168.1.101",
            },
            2: {
                "name": "cam-02 - Parking Lot",
                "type": "hdmi capture card (IP)",
                "source": "192.168.1.102",
            },
            3: {
                "name": "cam-03 - Entrance",
                "type": "dvr interface (IP)",
                "source": "192.168.1.103",
            },
            4: {"name": "cam-04 - Lobby", "type": "Webcam (USB)", "source": "0"},
        }

    st.title("⚡ APEX Video Analytics & Surveillance Dashboard")

    # ----------------------------------------------------
    # ١. بەشی هێما سەرەکییەکان (Metrics Bar)
    # ----------------------------------------------------
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(label="🎥 کامێرای چالاک", value="1 Live", delta="Connected")
    with col2:
        st.metric(label="🔍 ڕووداوی تۆمارکراو", value="24", delta="+3 ئەمڕۆ")
    with col3:
        st.metric(label="⚠️ ئاگادارکردنەوەکان", value="2 Alerts", delta="-1")
    with col4:
        st.metric(label="⚡ دۆخی AI Agent", value="Active", delta="Self-Healing")

    st.markdown("---")

    # ----------------------------------------------------
    # ٢. بەشی سەرەکی چاودێری ڤیدیۆ (Video Surveillance Core)
    # ----------------------------------------------------
    st.subheader("📹 ڕاستەوخۆی کامێراکان (Live Video Stream)")

    # بژاردەکانی هەڵبژاردنی سەرچاوەی ڤیدیۆ
    source_type = st.selectbox(
        "سەرچاوەی ڤیدیۆ (Video Source) هەڵبژێرە:",
        [
            "HDTV Capture Card (HDMI)",
            "Hikvision RTSP Stream",
            "Webcam Local (Default Camera)",
            "Video File Test",
        ],
    )

    # A. کاتێک HDTV Capture Card (HDMI) هەڵدەبژێردریت
    if source_type == "HDTV Capture Card (HDMI)":
        st.info(
            "🔌 کەیبڵی HDMIی DVR بە دانە شینەکەوە (Video Capture Card) بەستراوەتەوە."
        )

        col_cam, col_ctrl = st.columns([1, 2])
        with col_cam:
            cam_index = st.number_input(
                "کۆدی پۆڕتی Capture Index:", min_value=0, max_value=5, value=1
            )
            run_cam = st.checkbox("🔴 دەستپێکردنی چاودێری ڕاستەوخۆ (HDMI)", value=False)

        frame_placeholder = st.empty()

        if run_cam:
            cap = cv2.VideoCapture(int(cam_index))
            if not cap.isOpened():
                st.error(
                    f"❌ سیگناڵ لە پۆڕتی {cam_index} نەهات! ژمارەی Index بیگۆڕە (0 یان 2)."
                )
            else:
                st.toast("📹 سیگناڵی HDMI بە سەركەوتوویی بەستراوەتەوە!", icon="✅")
                while run_cam and cap.isOpened():
                    ret, frame = cap.read()
                    if not ret:
                        st.warning("⚠️ سیگناڵ پچڕا. دڵنیا ببەرەوە لە کەیبڵی HDMI.")
                        break

                    # نیشاندانی فریمی ڕاستەوخۆی HDMI
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    frame_placeholder.image(frame_rgb, use_container_width=True)
                cap.release()

    # B. کاتێک RTSP Stream هەڵدەبژێردریت
    elif source_type == "Hikvision RTSP Stream":
        rtsp_url = st.text_input(
            "ئەدرێسی RTSP بنووسە:",
            value="rtsp://admin:password@192.168.1.100:554/Streaming/Channels/101",
        )
        if st.button("بەستنەوە بە RTSP"):
            st.warning("هەوڵدان بۆ بەستنەوە بە تۆڕی Hikvision...")

    # C. کاتێک Webcam هەڵدەبژێردریت
    elif source_type == "Webcam Local (Default Camera)":
        st.write("بەکارهێنانی کامێرای سەرەکی لاپتۆپ.")

    # D. کاتێک فایلی ڤیدیۆ هەڵدەبژێردریت
    elif source_type == "Video File Test":
        st.file_uploader(
            "فایلی ڤیدیۆ هەڵبژێرە بۆ شیکاری (MP4, AVI):", type=["mp4", "avi"]
        )

    st.markdown("---")

    # ----------------------------------------------------
    # ٣. بەشی لۆگ و ئاگادارکردنەوەکانی سیستەم (Logs & Alerts)
    # ----------------------------------------------------
    st.subheader("📋 ئاگادارکردنەوەکان و مێژووی شیکاری (Logs & History)")

    tab1, tab2 = st.tabs(["⚠️ دوا ئاگادارکردنەوەکان", "🧠 بیرگەی AI Agent"])

    with tab1:
        st.write("• **10:42 AM**: بڕینی هێڵی پارێزراو لە کامێرای entrance_dvr")
        st.write("• **11:15 AM**: ناسینەوەی ئۆتۆمبێل لە شوێنی وەستان")

    with tab2:
        st.json(
            {
                "Last_Error": "re.error resolved via environment clean",
                "HDMI_Capture": "Plugged & Ready",
                "Status": "Healthy",
            }
        )


if __name__ == "__main__":
    show_dashboard()
