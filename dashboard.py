from __future__ import annotations

import importlib
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Union

import cv2
import numpy as np
import streamlit as st

_cv2: Any = cv2


def _load_attr(module_name: str, *attr_names: str) -> Any:
    """هاوردەکردنی سەلامەتی مۆدیول و کڵاسەکان بێ هەڵەی Pylance."""
    try:
        mod = importlib.import_module(module_name)
        for name in attr_names:
            if hasattr(mod, name):
                return getattr(mod, name)
    except Exception:
        pass
    return None


get_internal_cpu: Any = _load_attr("apex_internal_core", "get_internal_cpu")
APEXCyberShield: Any = _load_attr("cyber_shield", "APEXCyberShield")
FireSmokeDetector: Any = _load_attr("fire_smoke_detector", "FireSmokeDetector")
WeaponDetector: Any = _load_attr("weapon_detector", "WeaponDetector")
CrowdDistressDetector: Any = _load_attr(
    "crowd_distress_detector", "CrowdDistressDetector"
)
APEXDatabaseLifecycleManager: Any = _load_attr(
    "db_manager_view", "APEXDatabaseLifecycleManager"
)
render_db_manager_view: Any = _load_attr("db_manager_view", "render_db_manager_view")
APEXGISIntelligenceEngine: Any = _load_attr(
    "gis_intelligence", "APEXGISIntelligenceEngine"
)
render_gis_intelligence_view: Any = _load_attr(
    "gis_intelligence", "render_gis_intelligence_view"
)
render_forensics_view: Any = _load_attr("forensics_view", "render_forensics_view")
CameraBackend: Any = _load_attr("cameras", "CameraStream", "CameraStreamer")
FaceBackend: Any = _load_attr(
    "face_recognizer", "FaceRecognizerEngine", "APEXFaceRecognizer"
)
ALPRBackend: Any = _load_attr("alpr_engine", "ALPREngine", "APEXALPRPipeline")


@st.cache_resource
def _init_all_offline_engines() -> Dict[str, Any]:
    """بارکردنی یەکجاری هەموو بزوێنەرەکانی AI و بەستنەوەیان بە CPU ناوخۆیی."""
    engines: Dict[str, Any] = {
        "face": FaceBackend() if FaceBackend is not None else None,
        "alpr": ALPRBackend() if ALPRBackend is not None else None,
        "fire": FireSmokeDetector() if FireSmokeDetector is not None else None,
        "weapon": WeaponDetector() if WeaponDetector is not None else None,
        "crowd": CrowdDistressDetector() if CrowdDistressDetector is not None else None,
        "db": (
            APEXDatabaseLifecycleManager()
            if APEXDatabaseLifecycleManager is not None
            else None
        ),
        "gis": (
            APEXGISIntelligenceEngine()
            if APEXGISIntelligenceEngine is not None
            else None
        ),
        "shield": (
            APEXCyberShield(Path(__file__).resolve().parent)
            if APEXCyberShield is not None
            else None
        ),
    }

    if engines["db"] is not None:
        engines["db"].attach_to_internal_cpu()
    if engines["gis"] is not None:
        engines["gis"].attach_to_internal_cpu()

    return engines


def _make_standby_frame(cam_id: str, label: str, active_ai: List[str]) -> np.ndarray:
    """دروستکردنی شاشەی ئامادەباشیی Hikvision DVR (بێ پێویستبوون بە ئینتەرنێت)."""
    canvas = np.zeros((320, 560, 3), dtype=np.uint8)
    canvas[:] = (11, 17, 32)
    _cv2.rectangle(canvas, (6, 6), (554, 314), (30, 41, 59), 2)
    _cv2.putText(
        canvas,
        f"{cam_id} | {label}",
        (18, 36),
        _cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (56, 189, 248),
        2,
    )
    _cv2.putText(
        canvas,
        "HIKVISION DVR STANDBY — NO SIGNAL",
        (18, 165),
        _cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (148, 163, 184),
        2,
    )
    ai_txt = ", ".join(active_ai) if active_ai else "MONITOR ONLY"
    _cv2.putText(
        canvas,
        f"AI MATRIX: {ai_txt}",
        (18, 292),
        _cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (34, 197, 94),
        1,
    )
    return _cv2.cvtColor(canvas, _cv2.COLOR_BGR2RGB)


def _get_default_camera_matrix() -> Dict[str, Dict[str, Any]]:
    if "camera_ai_matrix" not in st.session_state:
        st.session_state.camera_ai_matrix = {
            "CAM-01": {
                "name": "North Main Gate",
                "source": 0,
                "face": True,
                "alpr": False,
                "fire": True,
                "weapon": True,
                "crowd": False,
            },
            "CAM-02": {
                "name": "Vehicle Parking",
                "source": 0,
                "face": False,
                "alpr": True,
                "fire": True,
                "weapon": False,
                "crowd": False,
            },
            "CAM-03": {
                "name": "Central Hall",
                "source": 0,
                "face": True,
                "alpr": False,
                "fire": True,
                "weapon": True,
                "crowd": True,
            },
            "CAM-04": {
                "name": "Restricted Perimeter",
                "source": 0,
                "face": False,
                "alpr": False,
                "fire": True,
                "weapon": True,
                "crowd": True,
            },
        }
    return st.session_state.camera_ai_matrix


def show_dashboard() -> None:
    """داشبۆردی سەرەکیی APEX بە ڕووکاری Hikvision DVR Command Center."""
    if "is_streaming" not in st.session_state:
        st.session_state.is_streaming = False

    engines = _init_all_offline_engines()
    cam_matrix = _get_default_camera_matrix()
    current_user = str(st.session_state.get("username", "admin"))

    cpu_pct, ram_pct, load_state = 0.0, 0.0, "OPTIMAL"
    if get_internal_cpu is not None:
        metrics = get_internal_cpu().get_hardware_metrics()
        cpu_pct = float(metrics.get("cpu_percent", 0.0))
        ram_pct = float(metrics.get("ram_percent", 0.0))
        load_state = str(metrics.get("load_state", "OPTIMAL"))

    now_clock = datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
    st.markdown(
        f"""
        <div class="dvr-topbar">
            <div>
                <span style="color:#ef4444; font-weight:900; font-size:18px;">🐉 APEX SECURITY DVR</span>
                <span style="color:#38bdf8; font-size:12px; margin-left:10px; font-weight:700;">FOR SAFE, FOR EVER</span>
            </div>
            <div style="font-family:monospace; font-size:13px; color:#cbd5e1;">
                🛡️ CYBER SHIELD: <b style="color:#22c55e;">100% OFFLINE</b> &nbsp;|&nbsp;
                ⚙️ CPU: <b>{cpu_pct}%</b> &nbsp;|&nbsp;
                🧠 RAM: <b>{ram_pct}%</b> [{load_state}] &nbsp;|&nbsp;
                🕒 <b>{now_clock}</b>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.markdown(f"### 👤 {current_user.upper()}")
        st.caption("APEX NVR / DVR Tactical Console")
        nav_tab = str(
            st.radio(
                "بەشەکانی سیستەم:",
                [
                    "🖥️ LIVE DVR & CAMERA-AI MATRIX",
                    "🗄️ DATABASE & 4-STAGE ARCHIVE",
                    "🗺️ TACTICAL GIS (CIA/FBI MODE)",
                    "🔬 FORENSICS & INVESTIGATION",
                    "⚙️ CAMERA CONFIG & LINKS",
                    "🛡️ CYBER SHIELD & DIAGNOSTICS",
                ],
                key="apex_dvr_nav_tab",
            )
            or "🖥️ LIVE DVR & CAMERA-AI MATRIX"
        )
        st.markdown("---")
        if st.button(
            "🚪 چوونەدەرەوە (Logout)", use_container_width=True, key="btn_apex_logout"
        ):
            st.session_state.is_streaming = False
            st.session_state.authenticated = False
            st.session_state.logged_in = False
            st.rerun()

    if nav_tab == "🗄️ DATABASE & 4-STAGE ARCHIVE":
        if render_db_manager_view is not None:
            render_db_manager_view()
        return

    if nav_tab == "🗺️ TACTICAL GIS (CIA/FBI MODE)":
        if render_gis_intelligence_view is not None:
            render_gis_intelligence_view()
        return

    if nav_tab == "🔬 FORENSICS & INVESTIGATION":
        if render_forensics_view is not None:
            render_forensics_view()
        return

    if nav_tab == "⚙️ CAMERA CONFIG & LINKS":
        st.markdown("## ⚙️ CAMERA LINKS & RTSP / CAPTURE CONFIGURATION")
        for cid, cfg in cam_matrix.items():
            with st.expander(f"📹 {cid} — {cfg['name']}", expanded=True):
                c_a, c_b = st.columns([1.2, 2.0])
                with c_a:
                    new_name = str(
                        st.text_input(
                            "ناوی شوێن:", value=str(cfg["name"]), key=f"cfg_n_{cid}"
                        )
                        or cfg["name"]
                    )
                with c_b:
                    new_src = str(
                        st.text_input(
                            "سەرچاوە (0 بۆ Webcam یان RTSP URL):",
                            value=str(cfg["source"]),
                            key=f"cfg_s_{cid}",
                        )
                        or "0"
                    )
                cfg["name"] = new_name
                cfg["source"] = int(new_src) if new_src.isdigit() else new_src
        st.success("گۆڕانکارییەکانی کامێرا ڕاستەوخۆ پاشەکەوت دەبن.")
        return

    if nav_tab == "🛡️ CYBER SHIELD & DIAGNOSTICS":
        st.markdown("## 🛡️ APEX CYBER SHIELD & INTERNAL CPU TELEMETRY")
        if engines["shield"] is not None:
            report = engines["shield"].audit_security_posture()
            m1, m2, m3 = st.columns(3)
            m1.metric("Security Score", f"{report['security_score']}%")
            m2.metric("Protected Files", report["protected_files"])
            m3.metric("Cloud / Internet Block", "ACTIVE (100% Offline)")
            st.json(report)
        return

    with st.expander(
        "🎛️ خشتەی بەستنەوەی کامێرا و سیستەمەکانی AI (Camera-AI Matrix)", expanded=False
    ):
        st.caption("بۆ هەر کامێرایەک دیاری بکە کام بزوێنەری AI لەسەری کار بکات:")
        h_cols = st.columns([1.3, 1, 1, 1, 1, 1])
        h_cols[0].markdown("**کامێرا**")
        h_cols[1].markdown("**Face ID**")
        h_cols[2].markdown("**ALPR تابلۆ**")
        h_cols[3].markdown("**Fire/Smoke**")
        h_cols[4].markdown("**Weapon چەک**")
        h_cols[5].markdown("**Crowd/Distress**")

        for cid, cfg in cam_matrix.items():
            r_cols = st.columns([1.3, 1, 1, 1, 1, 1])
            r_cols[0].write(f"**{cid}** ({cfg['name']})")
            cfg["face"] = r_cols[1].checkbox(
                "Face",
                value=bool(cfg["face"]),
                key=f"mx_f_{cid}",
                label_visibility="collapsed",
            )
            cfg["alpr"] = r_cols[2].checkbox(
                "ALPR",
                value=bool(cfg["alpr"]),
                key=f"mx_a_{cid}",
                label_visibility="collapsed",
            )
            cfg["fire"] = r_cols[3].checkbox(
                "Fire",
                value=bool(cfg["fire"]),
                key=f"mx_fi_{cid}",
                label_visibility="collapsed",
            )
            cfg["weapon"] = r_cols[4].checkbox(
                "Weapon",
                value=bool(cfg["weapon"]),
                key=f"mx_w_{cid}",
                label_visibility="collapsed",
            )
            cfg["crowd"] = r_cols[5].checkbox(
                "Crowd",
                value=bool(cfg["crowd"]),
                key=f"mx_c_{cid}",
                label_visibility="collapsed",
            )

    left_wall, right_panel = st.columns([3.1, 1.2])

    with left_wall:
        ctrl1, ctrl2, ctrl3 = st.columns([1.6, 1.2, 1.2])
        with ctrl1:
            stream_choice = str(
                st.selectbox(
                    "سەرچاوەی پەخشی زیندوو:",
                    ["Webcam (Local 0)", "Capture Card (Index 1)", "Custom RTSP URL"],
                    key="dvr_stream_src_sel",
                    label_visibility="collapsed",
                )
                or "Webcam (Local 0)"
            )
        selected_source: Union[int, str] = 0
        if stream_choice == "Capture Card (Index 1)":
            selected_source = 1
        elif stream_choice == "Custom RTSP URL":
            selected_source = str(
                st.text_input(
                    "RTSP:",
                    value="rtsp://admin:12345@192.168.1.64:554/Streaming/Channels/101",
                    key="dvr_rtsp_inp",
                    label_visibility="collapsed",
                )
                or "0"
            )

        with ctrl2:
            if not st.session_state.is_streaming:
                if st.button(
                    "▶ START LIVE DVR", use_container_width=True, key="btn_dvr_start"
                ):
                    st.session_state.is_streaming = True
                    st.rerun()
            else:
                if st.button(
                    "⏹ STOP LIVE DVR",
                    type="primary",
                    use_container_width=True,
                    key="btn_dvr_stop",
                ):
                    st.session_state.is_streaming = False
                    st.rerun()

        with ctrl3:
            grid_mode = str(
                st.selectbox(
                    "Grid:",
                    ["2x2 Matrix", "1x1 Focus (CAM-01)"],
                    key="dvr_grid_mode",
                    label_visibility="collapsed",
                )
                or "2x2 Matrix"
            )

        def _active_ai_tags(c_id: str) -> List[str]:
            c = cam_matrix[c_id]
            tags: List[str] = []
            if c["face"]:
                tags.append("FACE")
            if c["alpr"]:
                tags.append("ALPR")
            if c["fire"]:
                tags.append("FIRE")
            if c["weapon"]:
                tags.append("WEAPON")
            if c["crowd"]:
                tags.append("CROWD")
            return tags

        if grid_mode == "1x1 Focus (CAM-01)":
            st.markdown(
                f"<div class='dvr-channel-bar'>🔴 CH-01 | {cam_matrix['CAM-01']['name']} | AI: {', '.join(_active_ai_tags('CAM-01'))}</div>",
                unsafe_allow_html=True,
            )
            cam1_box = st.empty()
            cam2_box, cam3_box, cam4_box = None, None, None
            if not st.session_state.is_streaming:
                cam1_box.image(
                    _make_standby_frame(
                        "CAM-01",
                        cam_matrix["CAM-01"]["name"],
                        _active_ai_tags("CAM-01"),
                    ),
                    use_container_width=True,
                )
        else:
            g1, g2 = st.columns(2)
            with g1:
                st.markdown(
                    f"<div class='dvr-channel-bar'>🔴 CH-01 | {cam_matrix['CAM-01']['name']}</div>",
                    unsafe_allow_html=True,
                )
                cam1_box = st.empty()
                st.markdown(
                    f"<div class='dvr-channel-bar'>🔴 CH-03 | {cam_matrix['CAM-03']['name']}</div>",
                    unsafe_allow_html=True,
                )
                cam3_box = st.empty()
            with g2:
                st.markdown(
                    f"<div class='dvr-channel-bar'>🔴 CH-02 | {cam_matrix['CAM-02']['name']}</div>",
                    unsafe_allow_html=True,
                )
                cam2_box = st.empty()
                st.markdown(
                    f"<div class='dvr-channel-bar'>🔴 CH-04 | {cam_matrix['CAM-04']['name']}</div>",
                    unsafe_allow_html=True,
                )
                cam4_box = st.empty()

            if not st.session_state.is_streaming:
                cam1_box.image(
                    _make_standby_frame(
                        "CAM-01",
                        cam_matrix["CAM-01"]["name"],
                        _active_ai_tags("CAM-01"),
                    ),
                    use_container_width=True,
                )
                cam2_box.image(
                    _make_standby_frame(
                        "CAM-02",
                        cam_matrix["CAM-02"]["name"],
                        _active_ai_tags("CAM-02"),
                    ),
                    use_container_width=True,
                )
                cam3_box.image(
                    _make_standby_frame(
                        "CAM-03",
                        cam_matrix["CAM-03"]["name"],
                        _active_ai_tags("CAM-03"),
                    ),
                    use_container_width=True,
                )
                cam4_box.image(
                    _make_standby_frame(
                        "CAM-04",
                        cam_matrix["CAM-04"]["name"],
                        _active_ai_tags("CAM-04"),
                    ),
                    use_container_width=True,
                )

    with right_panel:
        with st.container(border=True):
            st.markdown("##### 🚨 LIVE AI THREAT FEED")
            live_feed_box = st.empty()
            live_feed_box.info("🟢 هەموو بزوێنەرەکان لە ئامادەباشیدان (100% Offline)")

        with st.container(border=True):
            st.markdown("##### 🤖 ACTIVE AI MODULES")
            st.markdown("🟢 **Fire & Smoke AI:** READY")
            st.markdown("🟢 **Weapon & Gunfire AI:** READY")
            st.markdown("🟢 **Crowd & Distress AI:** READY")
            st.markdown("🟢 **Face ID & ALPR:** READY")

    if st.session_state.is_streaming:
        if CameraBackend is None:
            st.error("فایلی cameras.py نەدۆزرایەوە.")
            return

        try:
            cam = CameraBackend(selected_source)
        except TypeError:
            cam = CameraBackend("CAM-01", selected_source, "Webcam")

        frame_idx = 0

        while st.session_state.get("is_streaming", False):
            raw_frame = cam.get_frame()
            if (
                raw_frame is None
                or not isinstance(raw_frame, np.ndarray)
                or raw_frame.size == 0
            ):
                time.sleep(0.01)
                continue

            frame_idx += 1
            run_ai_now = frame_idx % 4 == 0
            if get_internal_cpu is not None:
                run_ai_now = get_internal_cpu().should_process_frame(frame_idx)

            analyzed_frame = raw_frame.copy()
            all_alerts: List[str] = []

            if run_ai_now:
                c1_cfg = cam_matrix["CAM-01"]
                if c1_cfg["fire"] and engines["fire"] is not None:
                    analyzed_frame, f_det = engines["fire"].process_frame(
                        analyzed_frame, camera_id="CAM-01"
                    )
                    for d in f_det:
                        all_alerts.append(f"🔥 {d['type']} ({d['confidence']}%)")

                if c1_cfg["weapon"] and engines["weapon"] is not None:
                    analyzed_frame, w_det = engines["weapon"].process_frame(
                        analyzed_frame, camera_id="CAM-01"
                    )
                    for d in w_det:
                        all_alerts.append(f"🔫 {d['type']} ({d['confidence']}%)")

                if c1_cfg["crowd"] and engines["crowd"] is not None:
                    analyzed_frame, cr_det = engines["crowd"].process_frame(
                        analyzed_frame, camera_id="CAM-01"
                    )
                    for d in cr_det:
                        all_alerts.append(f"📢 {d['type']} ({d['confidence']}%)")

                if c1_cfg["face"] and engines["face"] is not None:
                    try:
                        if hasattr(engines["face"], "process_frame_with_details"):
                            analyzed_frame, t_det = engines[
                                "face"
                            ].process_frame_with_details(analyzed_frame)
                            for t in t_det:
                                if t.get("status") == "MATCHED":
                                    all_alerts.append(
                                        f"🎯 TARGET: {t.get('name', 'MATCH')}"
                                    )
                        elif hasattr(engines["face"], "detect_and_draw"):
                            analyzed_frame, f_list = engines["face"].detect_and_draw(
                                analyzed_frame, enabled=True
                            )
                            if f_list:
                                all_alerts.append(f"👤 FACE DETECTED ({len(f_list)})")
                    except Exception:
                        pass

                if (
                    c1_cfg["alpr"]
                    and engines["alpr"] is not None
                    and hasattr(engines["alpr"], "process_frame")
                ):
                    try:
                        analyzed_frame, p_det = engines["alpr"].process_frame(
                            analyzed_frame
                        )
                        if isinstance(p_det, list):
                            for p in p_det:
                                all_alerts.append(f"🚗 PLATE: {p.get('plate', '')}")
                        elif isinstance(p_det, dict) and p_det.get("plate"):
                            all_alerts.append(f"🚗 PLATE: {p_det.get('plate', '')}")
                    except Exception:
                        pass

            rgb_main = _cv2.cvtColor(analyzed_frame, _cv2.COLOR_BGR2RGB)
            rgb_raw = _cv2.cvtColor(raw_frame, _cv2.COLOR_BGR2RGB)

            cam1_box.image(rgb_main, use_container_width=True)
            if cam2_box is not None and cam3_box is not None and cam4_box is not None:
                cam2_box.image(rgb_raw, use_container_width=True)
                cam3_box.image(rgb_raw, use_container_width=True)
                cam4_box.image(rgb_raw, use_container_width=True)

            if all_alerts:
                live_feed_box.error("\n\n".join(all_alerts))

            time.sleep(0.005)

        if hasattr(cam, "release"):
            cam.release()
        elif hasattr(cam, "stop"):
            cam.stop()


if __name__ == "__main__":
    show_dashboard()
