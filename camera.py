import streamlit as st

# پشکنینی سەلامەتی بۆ کتێبخانەکان بۆ ئەوەی لەسەر کلاود کێشە دروست نەبێت
try:
    import cv2
    OPENCV_LOADED = True
except ImportError:
    OPENCV_LOADED = False

try:
    from deepface import DeepFace
    DEEPFACE_LOADED = True
except ImportError:
    DEEPFACE_LOADED = False

def render_camera_module():
    st.subheader("📷 APEX Smart Surveillance & Camera Hub")
    st.write("---")

    # دیاریکردنی جۆری کامێرا (خۆڕایی یان پرێمیەم)
    cam_option = st.sidebar.radio(
        "Select Camera Tier",
        ["💻 Free: Laptop Webcam", "🔒 Paid/Premium: Wi-Fi & IP Cameras"]
    )

    if cam_option == "💻 Free: Laptop Webcam":
        st.info("🟢 Free Tier: Using built-in laptop camera for real-time monitoring.")
        
        run_webcam = st.checkbox("Start Laptop Camera Stream")
        
        if run_webcam:
            if not OPENCV_LOADED:
                st.error("OpenCV is not loaded properly in this environment.")
                return

            frame_window = st.image([])
            cap = cv2.VideoCapture(0) # 0 بۆ کامێرای لاپتۆپە

            if not cap.isOpened():
                st.error("Could not access laptop webcam.")
            else:
                try:
                    while run_webcam:
                        ret, frame = cap.read()
                        if not ret:
                            st.warning("Failed to grab frame from laptop camera.")
                            break
                        
                        # گۆڕینی ڕەنگ بۆ ڕوکاری Streamlit
                        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        
                        # ئەگەر DeepFace بەردەست بوو، دەتوانیت لێرە پشکنینی ڕوخسار بکەیت
                        if DEEPFACE_LOADED:
                            # نموونەی پشکنینی خێرا
                            pass

                        frame_window.image(frame)
                finally:
                    cap.release()

    elif cam_option == "🔒 Paid/Premium: Wi-Fi & IP Cameras":
        st.warning("⭐ Premium Feature: Connect external Hikvision / IP / Wi-Fi cameras via RTSP.")
        
        # لێرە داوای لینک یان زانیاری کامێرای وایفای دەکرێت
        rtsp_url = st.text_input(
            "Enter Wi-Fi / RTSP Camera Stream URL", 
            placeholder="rtsp://admin:password@192.168.1.100:554/stream"
        )
        
        connect_btn = st.button("Connect Wi-Fi Camera")
        
        if connect_btn:
            if rtsp_url:
                st.success(f"Connecting to secure Wi-Fi stream: {rtsp_url}")
                if not OPENCV_LOADED:
                    st.error("OpenCV is required for RTSP stream handling.")
                else:
                    # تاقیکردنەوەی پەیوەندیکردن بە وایفای دوربینەکە
                    try:
                        wifi_cap = cv2.VideoCapture(rtsp_url)
                        if wifi_cap.isOpened():
                            st.success("Successfully connected to Wi-Fi camera stream!")
                            wifi_cap.release()
                        else:
                            st.error("Failed to connect. Please check the RTSP URL or network connection.")
                    except Exception as e:
                        st.error(f"Connection error: {e}")
            else:
                st.warning("Please enter a valid RTSP stream link.")

if __name__ == "__main__":
    render_camera_module()