import cv2
import time
import streamlit as st

# Explicit alias used by static analyzers and to avoid any imported-name lookup ambiguity.
cvtColor = cv2.cvtColor

def start_multi_camera_stream(box1, box2, cam1_type="laptop", cam1_url="", cam2_type="rtsp", cam2_url="", toggle_key="toggle_all_cams"):
    """ئیشپێکردنی هاوکاتی کامێراکان بە بێ بەکارهێنانی Session State"""
    
    # کردەنەوەی کامێرای ١
    cap1 = cv2.VideoCapture(0, cv2.CAP_DSHOW) if cam1_type == "laptop" else cv2.VideoCapture(cam1_url)
    if cam1_type == "laptop" and not cap1.isOpened():
        cap1 = cv2.VideoCapture(0)

    # کردەنەوەی کامێرای ٢ (RTSP/LAN)
    cap2 = cv2.VideoCapture(cam2_url) if (cam2_type == "rtsp" and cam2_url) else None

    # بازنەی خێرا بۆ نیشاندانی فریمەکان
    while st.session_state.get(toggle_key, False):
        # خوێندنەوەی کامێرای ١
        if cap1 and cap1.isOpened():
            ret1, frame1 = cap1.read()
            if ret1 and frame1 is not None:
                f1 = cv2.resize(frame1, (640, 360))
                f1_rgb = cv2.cvtColor(f1, cv2.COLOR_BGR2RGB)
                box1.image(f1_rgb, channels="RGB", use_container_width=True)

        # خوێندنەوەی کامێرای ٢
        if cap2 and cap2.isOpened():
            ret2, frame2 = cap2.read()
            if ret2 and frame2 is not None:
                f2 = cv2.resize(frame2, (640, 360))
                f2_rgb = cv2.cvtColor(f2, cv2.COLOR_BGR2RGB)
                box2.image(f2_rgb, channels="RGB", use_container_width=True)

        time.sleep(0.01)  # ڕێگری لە دروستبوونی فشار لەسەر CPU

    # بەستنی کامێراکان لە کاتی وەستاندا
    if cap1:
        cap1.release()
    if cap2:
        cap2.release()