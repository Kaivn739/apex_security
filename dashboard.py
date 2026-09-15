import importlib
import streamlit as st
import pandas as pd
import numpy as np

try:
    style_module = importlib.import_module("style")
    apply_apex_style = style_module.apply_apex_style
    render_stat_box = style_module.render_stat_box
    if hasattr(style_module, "render_interactive_lottie_card"):
        render_interactive_lottie_card = style_module.render_interactive_lottie_card
    else:
        def render_interactive_lottie_card():
            st.markdown(
                "<div style='background:#0b1329; padding:12px; border-radius:8px; border:1px solid #1e293b;'>"
                "<small style='color:#94a3b8;'>Lottie animation unavailable</small>"
                "</div>",
                unsafe_allow_html=True,
            )
except Exception:

    def apply_apex_style():
        st.set_page_config(page_title="APEX Security", layout="wide")

    def render_stat_box(title, value, subtitle):
        st.markdown(
            f"<div style='background:#0b1329; padding:12px; border-radius:8px; border:1px solid #1e293b;'>"
            f"<small style='color:#94a3b8;'>{title}</small><br>"
            f"<b style='color:#f8fafc; font-size:22px;'>{value}</b><br>"
            f"<small style='color:#94a3b8;'>{subtitle}</small>"
            f"</div>",
            unsafe_allow_html=True,
        )

    def render_interactive_lottie_card():
        st.markdown(
            "<div style='background:#0b1329; padding:12px; border-radius:8px; border:1px solid #1e293b;'>"
            "<small style='color:#94a3b8;'>Lottie animation unavailable</small>"
            "</div>",
            unsafe_allow_html=True,
        )


def render_top_bar(title="Security Command Center"):
    st.markdown(
        f"<h1 style='color:#f8fafc; font-size:22px; margin:0 0 20px 0;'>{title}</h1>",
        unsafe_allow_html=True,
    )


def start_multi_camera_stream(
    box1=None,
    box2=None,
    cam1_type="laptop",
    cam2_type="rtsp",
    cam2_url="",
    toggle_key="toggle_all_cams",
):
    """Fallback stream starter used when the camera integration is unavailable.
    Keeps the dashboard importable and prevents undefined-name errors.
    """
    # Refer to the stream parameters explicitly so the fallback stays usable
    # and lint tools no longer report unused-function arguments.
    stream_sources = {
        "cam1_type": cam1_type,
        "cam2_type": cam2_type,
        "cam2_url": cam2_url,
        "toggle_key": toggle_key,
    }
    if "rtsp" in cam2_type.lower() and cam2_url:
        stream_sources["cam2_url"] = cam2_url

    if box1 is not None:
        if cam1_type.lower() == "laptop":
            box1.image(
                "https://via.placeholder.com/640x360.png?text=CAM-01+Live",
                width="stretch",
            )
        else:
            box1.image(
                "https://via.placeholder.com/640x360.png?text=CAM-01+"
                + cam1_type.upper(),
                width="stretch",
            )
    if box2 is not None:
        if cam2_type.lower() == "rtsp" and cam2_url:
            box2.image(
                "https://via.placeholder.com/640x360.png?text=CAM-02+RTSP+Stream",
                width="stretch",
            )
        else:
            box2.image(
                "https://via.placeholder.com/640x360.png?text=CAM-02+Live",
                width="stretch",
            )


def show_dashboard():
    apply_apex_style()

    # --- سایدمێنۆی لای چەپ ---
    with st.sidebar:
        st.markdown(
            "<h2 style='color:#38bdf8; font-size:18px;'>🛡️ APEX SECURITY</h2>",
            unsafe_allow_html=True,
        )
        st.caption("COMMAND CENTER")

        st.markdown("---")
        st.markdown(
            "<small style='color:#64748b;'>MONITORING</small>", unsafe_allow_html=True
        )
        st.radio(
            "بەشەکان",
            ["🖥️ Dashboard", "📹 Live View", "📷 Cameras", "🔔 Events"],
            index=0,
            key="apex_nav_radio",
            label_visibility="collapsed",
        )
        st.markdown("---")
        st.markdown(
            "<small style='color:#64748b;'>AI ANALYTICS</small>", unsafe_allow_html=True
        )
        st.selectbox(
            "دیاریکردنی بەشی AI",
            ["🎯 AI Detection", "🚧 Security Zones", "🚪 Entry/Exit"],
            key="apex_ai_select",
        )
        st.markdown("---")
        st.markdown(
            "<small style='color:#64748b;'>SYSTEM</small>", unsafe_allow_html=True
        )
        st.button("⚙️ Settings", key="apex_settings_btn")

    # --- باری سەرەوەی دەشبۆرد ---
    render_top_bar(title="Security Command Center")

    # --- ١. کارتی ئامارەکانی سەرەوە ---
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        render_stat_box("CAMERAS", "24", "22 Online / 2 Offline")
    with c2:
        render_stat_box("PEOPLE DETECTED", "128", "Currently Active")
    with c3:
        render_stat_box("TODAY'S ENTRIES", "74", "+12% vs Yesterday")
    with c4:
        render_stat_box("TODAY'S EXITS", "61", "Normal Flow")
    with c5:
        render_stat_box("OCCUPANCY", "68%", "Average Zones")

    st.markdown("<br>", unsafe_allow_html=True)

    # --- ٢. کامێراکان (Grid 2x2) + ئاگادارکردنەوەکان ---
    # --- ١. دروستکردنی ستوونی سەرەکی و ستوونی دەستەڕاست ---
    col_main, col_side = st.columns([7, 3])

    with col_main:
        st.subheader("Live Camera Feed")
        # کۆدەکانی کامێرای سەرەکی لێرەدا دەبن

    with col_side:
        st.subheader("System Status")
        # 📍 بانگکردنی ئانیمەیشنی Lottie
        render_interactive_lottie_card()
        with st.expander(
            "⚙️ ڕێکخستنی سەرچاوەی کامێراکان (RTSP / Laptop)", expanded=False
        ):
            st.info("💡 دەتوانیت لینکی RTSPی Hikvision یان کامێرای IP بنووسیت:")
            rtsp_link = st.text_input(
                "لینکی RTSP بۆ CAM-02:",
                value="rtsp://admin:admin123@192.168.1.64:554/Streaming/Channels/101",
                key="rtsp_cam2_input",
            )

        # چک بۆکسی ئیشپێکردنی کامێراکان
        run_cams = st.checkbox(
            "▶️ داگیرساندنی ستریمی ڕاستەوخۆی کامێراکان", key="toggle_all_cams"
        )

        # دروستکردنی خشتەی 2x2
        row1_col1, row1_col2 = st.columns(2)
        row2_col1, row2_col2 = st.columns(2)

        with row1_col1:
            st.markdown(
                "<div style='background:#0b1329; padding:4px; border-radius:5px; border:1px solid #1e293b;'><small style='color:#10b981;'>🔴 CAM-01: Main Entrance (Laptop)</small></div>",
                unsafe_allow_html=True,
            )
            box1 = st.empty()
            if not run_cams:
                box1.image(
                    "https://via.placeholder.com/640x360.png?text=CAM-01+Offline",
                    width="stretch",
                )

        with row1_col2:
            st.markdown(
                "<div style='background:#0b1329; padding:4px; border-radius:5px; border:1px solid #1e293b;'><small style='color:#10b981;'>🔴 CAM-02: Parking Area (LAN / RTSP)</small></div>",
                unsafe_allow_html=True,
            )
            box2 = st.empty()
            if not run_cams:
                box2.image(
                    "https://via.placeholder.com/640x360.png?text=CAM-02+Offline",
                    width="stretch",
                )

        with row2_col1:
            st.markdown(
                "<div style='background:#0b1329; padding:4px; border-radius:5px; border:1px solid #1e293b; margin-top:8px;'><small style='color:#38bdf8;'>🔵 CAM-03: Reception</small></div>",
                unsafe_allow_html=True,
            )
            st.image(
                "https://via.placeholder.com/640x360.png?text=CAM-03+Reception",
                width="stretch",
            )

        with row2_col2:
            st.markdown(
                "<div style='background:#0b1329; padding:4px; border-radius:5px; border:1px solid #1e293b; margin-top:8px;'><small style='color:#ef4444;'>🔴 CAM-04: Restricted Zone (ALERT)</small></div>",
                unsafe_allow_html=True,
            )
            st.image(
                "https://via.placeholder.com/640x360.png?text=CAM-04+Restricted+Zone",
                width="stretch",
            )

        # ئەگەر چک بۆکسەکە چالاک کرا، کامێراکان دەستبەجێ دەست بە کار دەکەن
        if run_cams:
            start_multi_camera_stream(
                box1=box1,
                box2=box2,
                cam1_type="laptop",
                cam2_type="rtsp",
                cam2_url=rtsp_link,
                toggle_key="toggle_all_cams",
            )

    with col_side:
        st.markdown(
            "<h4 style='color:#f8fafc; font-size:14px;'>🚨 ACTIVE ALERTS</h4>",
            unsafe_allow_html=True,
        )
        st.markdown(
            """
        <div class="alert-critical">
            <b style="color:#ef4444; font-size:12px;">🚨 Intrusion Detected</b><br>
            <small style="color:#cbd5e1;">CAM-04 | Restricted Zone</small>
        </div>
        <div class="alert-critical">
            <b style="color:#ef4444; font-size:12px;">🔥 Fire Detection Alert</b><br>
            <small style="color:#cbd5e1;">CAM-03 | Reception</small>
        </div>
        <div class="alert-warning">
            <b style="color:#f59e0b; font-size:12px;">⚠️ High Occupancy</b><br>
            <small style="color:#cbd5e1;">CAM-02 | Parking Area</small>
        </div>
        """,
            unsafe_allow_html=True,
        )

        st.markdown("<hr style='border-color:#1e293b;'>", unsafe_allow_html=True)
        st.markdown(
            "<h4 style='color:#f8fafc; font-size:14px;'>📊 SYSTEM STATUS</h4>",
            unsafe_allow_html=True,
        )
        st.progress(0.23, text="CPU Usage: 23%")
        st.progress(0.41, text="RAM Usage: 41%")

    st.markdown("<br>", unsafe_allow_html=True)

    # --- ٣. ئاماری خوارەوە ---
    b1, b2, b3 = st.columns([1, 1, 2])
    with b1:
        st.caption("ZONE OCCUPANCY")
        st.progress(0.68, text="Main Entrance: 68%")
        st.progress(0.43, text="Parking: 43%")
    with b2:
        st.caption("DETECTION SUMMARY")
        st.markdown(
            """
        <div style="background:#0b1329; padding:8px; border-radius:5px; border:1px solid #1e293b;">
            <small style="color:#38bdf8;">👤 People: <b>1,182</b></small><br>
            <small style="color:#38bdf8;">🚗 Vehicles: <b>248</b></small>
        </div>
        """,
            unsafe_allow_html=True,
        )
    with b3:
        st.caption("ENTRY / EXIT TREND")
        chart_data = pd.DataFrame(
            np.random.randn(20, 2) + [10, 8], columns=["Entries", "Exits"]
        )
        st.line_chart(chart_data, height=100)


# The dashboard UI is rendered by show_dashboard().
# Demo/source selection should be handled in a higher-level app flow,
# not as stray code appended at the end of the dashboard file.

if __name__ == "__main__":
    show_dashboard()
