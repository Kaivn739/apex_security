try:
    import streamlit as st
except ImportError:  # pragma: no cover
    st = None

try:
    import folium  # type: ignore
    from streamlit_folium import st_folium  # type: ignore
except ImportError:  # pragma: no cover
    folium = None
    st_folium = None


def render_camera_map(selected_target_id=None):
    """
    نیشاندانی نەخشەی کارلێککار (Interactive Map)ی کامێراکان و ڕێڕەوی تێپەڕبوونی تارگێت
    """
    if folium is None or st_folium is None:
        if st is not None:
            st.error(
                "Map dependencies are missing. Install them with: pip install folium streamlit-folium"
            )
        return

    cameras_geo = {
        1: {
            "name": "CAM-01 Main Gate",
            "coords": [36.1911, 44.0092],
            "status": "CLEAR",
        },
        2: {
            "name": "CAM-02 Parking Area",
            "coords": [36.1920, 44.0098],
            "status": "ALERT",
        },
        3: {
            "name": "CAM-03 Security Zone",
            "coords": [36.1928, 44.0105],
            "status": "CLEAR",
        },
        4: {
            "name": "CAM-04 Perimeter",
            "coords": [36.1935, 44.0112],
            "status": "ALERT",
        },
    }

    apex_map = folium.Map(
        location=[36.1922, 44.0100], zoom_start=17, tiles="openstreetmap"
    )

    target_path = [
        cameras_geo[1]["coords"],
        cameras_geo[2]["coords"],
        cameras_geo[4]["coords"],
    ]

    folium.PolyLine(
        locations=target_path,
        color="#ef4444",
        weight=4,
        opacity=0.8,
        dash_array="10",
        tooltip="🚨 TARGET MOVEMENT PATH",
    ).add_to(apex_map)

    for cam_id, info in cameras_geo.items():
        is_alert = info["status"] == "ALERT"
        color = "red" if is_alert else "green"
        icon_type = "exclamation-triangle" if is_alert else "video-camera"

        popup_html = f"""
        <div style='font-family: sans-serif; color: #020617;'>
            <b>📹 {info['name']}</b><br>
            <b>دۆخ:</b> <span style='color: {'red' if is_alert else 'green'};'>{'🔴 ALERT' if is_alert else '🟢 CLEAR'}</span><br>
            <b>کۆئۆردینات:</b> {info['coords'][0]}, {info['coords'][1]}
        </div>
        """

        folium.Marker(
            location=info["coords"],
            popup=popup_html,
            tooltip=f"{info['name']} ({'🚨 TARGET DETECTED' if is_alert else 'NORMAL'})",
            icon=folium.Icon(color=color, icon=icon_type, prefix="fa"),
        ).add_to(apex_map)

    st_folium(apex_map, use_container_width=True, height=500)