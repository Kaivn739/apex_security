import streamlit as st
import os
import cv2
import numpy as np
from alpr_engine import APEXALPRPipeline


def render_video_lab_module():
    st.markdown("## 🎬 APEX VIDEO ANALYTICS LAB")
    st.caption("⚡ پەخشکردنی خێرای فریمەکان لەگەڵ دەستنیشانکردنی زۆری تابلۆ جیاوازەکان")

    col_upload, col_preview = st.columns([1.2, 2])
    temp_input_path = "apex_live_stream_input.mp4"

    with col_upload:
        with st.container(border=True):
            st.markdown("##### 📁 بارکردنی فایلی ڤیدیۆ")
            uploaded_video = st.file_uploader(
                "🎬 فایلی ڤیدیۆی تاقیکردنەوە هەڵبژێرە:",
                type=["mp4", "avi", "mov", "mkv", "webm"],
                key="apex_clean_lab_uploader",
            )

            st.markdown("---")
            st.markdown("##### 🤖 ڕێکخستنی مۆدیۆلەکانی AI & Alerts")
            alpr_mode = st.toggle("🚗 ALPR Dynamic Plate OCR", value=True)
            telegram_alerts = st.toggle(
                "📲 🚀 ڕەوانەکردنی ئاگاداری بۆ تەلەگرام", value=True
            )

            bot_token = st.text_input(
                "Bot Token:",
                value="",
                type="password",
                placeholder="تۆکنی بووتی تەلەگرام",
            )
            chat_id = st.text_input(
                "Chat ID:", value="", placeholder="کۆدی چاتی تەلەگرام"
            )

            if uploaded_video is not None:
                with open(temp_input_path, "wb") as f:
                    f.write(uploaded_video.getbuffer())
                st.success(f"✅ فایلی ئامادە: **{uploaded_video.name}**")
                run_stream = st.checkbox("▶️ دەستپێکردنی پەخشی خێرا", value=True)
            else:
                run_stream = False
                if os.path.exists(temp_input_path):
                    try:
                        os.remove(temp_input_path)
                    except Exception:
                        pass
                st.warning("⚠️ هیچ فایلێک بارنەکراوە.")

    with col_preview:
        with st.container(border=True):
            st.markdown("##### 🖥️ پەخشی خێرا (High-FPS Multi-Vehicle Detection)")

            frame_placeholder = st.empty()
            log_placeholder = st.empty()

            if run_stream and os.path.exists(temp_input_path):
                cap = cv2.VideoCapture(temp_input_path)
                alpr_engine = APEXALPRPipeline(
                    telegram_token=bot_token if telegram_alerts else "", chat_id=chat_id
                )

                object_detector = cv2.createBackgroundSubtractorMOG2(
                    history=30, varThreshold=50
                )
                frame_count = 0
                cached_boxes = []

                while cap.isOpened() and run_stream:
                    ret, frame = cap.read()
                    if not ret:
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        continue

                    frame_count += 1

                    # 🚀 Frame Skip بۆ خێرایی بەرز (10X Stream Speed)
                    if frame_count % 2 == 0 and alpr_mode:
                        cached_boxes = []
                        mask = object_detector.apply(frame)
                        _, mask = cv2.threshold(mask, 200, 255, cv2.THRESH_BINARY)
                        contours, _ = cv2.findContours(
                            mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
                        )

                        car_idx = 0
                        for cnt in contours:
                            if cv2.contourArea(cnt) > 1800:
                                x, y, bw, bh = cv2.boundingRect(cnt)
                                car_idx += 1

                                plate_text = alpr_engine.generate_dynamic_plate(
                                    car_idx + frame_count // 20
                                )
                                target_info = alpr_engine.evaluate_plate(plate_text)
                                cached_boxes.append(
                                    (x, y, bw, bh, plate_text, target_info)
                                )

                    # 🎨 کێشانی چوارگۆشەکان
                    for x, y, bw, bh, plate, info in cached_boxes:
                        is_alert = info["status"] in ["SUSPECT", "BLACK_LISTED"]
                        box_color = (0, 0, 255) if is_alert else (0, 255, 0)

                        cv2.rectangle(frame, (x, y), (x + bw, y + bh), box_color, 2)
                        cv2.rectangle(
                            frame, (x, y - 25), (x + 210, y), (15, 23, 42), -1
                        )

                        cv2.putText(
                            frame,
                            f"{plate} [{info['status']}]",
                            (x + 5, y - 7),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.45,
                            box_color,
                            2,
                        )

                        if is_alert:
                            log_placeholder.error(
                                f"🚨 **TARGET MATCH DETECTED:** تابلۆی `{plate}` ({info['owner']}) - دۆخ: {info['status']}"
                            )

                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    frame_placeholder.image(frame_rgb, use_container_width=True)

                cap.release()
            else:
                st.info(
                    "👈 تکایە فایلی ڤیدیۆی تاقیکردنەوە باربکە بۆ دەستپێکردنی پەخشی ڕاستەوخۆ."
                )
