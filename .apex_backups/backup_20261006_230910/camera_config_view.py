import streamlit as st


def render_camera_config_module():
    st.markdown("## ⚙️ MAIN NETWORK CAMERA CONFIGURATION")
    st.caption("تۆمارکردن و ڕێکخستنی ناونیشانی کامێراکان (IP / RTSP / DVR)")

    col_c1, col_c2 = st.columns([1.5, 1])
    with col_c1:
        with st.container(border=True):
            st.markdown("##### 📹 کامێرا چالاکەکانی سیستەم")
            for cid, cdata in st.session_state.camera_config.items():
                st.text(
                    f"ID: {cid} | {cdata['name']} | {cdata['type']} -> {cdata['source']}"
                )

    with col_c2:
        with st.container(border=True):
            st.markdown("##### ➕ زیادکردنی کامێرای نوێ")
            new_cam_name = st.text_input("ناوی کامێرا:", placeholder="CAM-05 Gate")
            new_cam_type = st.selectbox(
                "جۆری پەیوەندی:", ["LAN Cable (IP)", "RTSP Stream", "DVR Interface"]
            )
            new_cam_src = st.text_input(
                "ناونیشانی Source/RTSP:", placeholder="192.168.1.105"
            )
            if st.button("💾 پاشەکەوتکردنی کامێرا", use_container_width=True):
                if new_cam_name and new_cam_src:
                    new_id = max(st.session_state.camera_config.keys()) + 1
                    st.session_state.camera_config[new_id] = {
                        "name": new_cam_name,
                        "type": new_cam_type,
                        "source": new_cam_src,
                    }
                    st.success("✅ کامێرای نوێ بە سەرکەوتوویی زیادکرا!")
                    st.rerun()