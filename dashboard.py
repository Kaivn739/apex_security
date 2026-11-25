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
AsyncAIWorkerBackend: Any = _load_attr("cameras", "AsyncAIWorker")
FaceBackend: Any = _load_attr(
    "face_recognizer", "FaceRecognizerEngine", "APEXFaceRecognizer"
)
ALPRBackend: Any = _load_attr("alpr_engine", "ALPREngine", "APEXALPRPipeline")


def _inject_dvr_styles() -> None:
    """چەسپاندنی ستایلی تەواوی Hikvision Tactical DVR لەناو Streamlit."""
    st.markdown(
        """
        <style>
        .dvr-topbar {
            background: linear-gradient(90deg, #090d16 0%, #111827 50%, #090d16 100%);
            border: 1px solid #1e293b;
            border-left: 4px solid #ef4444;
            border-radius: 6px;
            padding: 10px 16px;
            margin-bottom: 14px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.45);
        }
        .dvr-channel-bar {
            background: #0f172a;
            color: #e2e8f0;
            border: 1px solid #334155;
            border-bottom: none;
            border-radius: 6px 6px 0 0;
            padding: 5px 10px;
            font-family: monospace;
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 0.4px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


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

    if engines["db"] is not None and hasattr(engines["db"], "attach_to_internal_cpu"):
        engines["db"].attach_to_internal_cpu()
    if engines["gis"] is not None and hasattr(engines["gis"], "attach_to_internal_cpu"):
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


def _open_camera_stream(cam_id: str, source: Union[int, str], label: str) -> Any:
    if CameraBackend is None:
        return None
    try:
        return CameraBackend(source=source, cam_type="Webcam", cam_id=cam_id)
    except TypeError:
        try:
            return CameraBackend(source)
        except TypeError:
            return CameraBackend(cam_id, source, label)


def _close_camera_stream(cam_obj: Any) -> None:
    if cam_obj is None:
        return
    if hasattr(cam_obj, "release"):
        cam_obj.release()
    elif hasattr(cam_obj, "stop"):
        cam_obj.stop()


def _analyze_channel_frame(
    frame: np.ndarray,
    cam_id: str,
    cfg: Dict[str, Any],
    engines: Dict[str, Any],
) -> tuple[np.ndarray, List[str]]:
    """شیکارکردنی فریمێک بە پێی ڕێکخستنی AIـی تایبەت بە هەر کامێرایەک."""
    analyzed = frame.copy()
    alerts: List[str] = []

    if cfg.get("fire") and engines["fire"] is not None:
        try:
            analyzed, f_det = engines["fire"].process_frame(analyzed, camera_id=cam_id)
            for d in f_det:
                alerts.append(f"[{cam_id}] 🔥 {d['type']} ({d['confidence']}%)")
        except Exception:
            pass

    if cfg.get("weapon") and engines["weapon"] is not None:
        try:
            analyzed, w_det = engines["weapon"].process_frame(analyzed, camera_id=cam_id)
            for d in w_det:
                alerts.append(f"[{cam_id}] 🔫 {d['type']} ({d['confidence']}%)")
        except Exception:
            pass

    if cfg.get("crowd") and engines["crowd"] is not None:
        try:
            analyzed, cr_det = engines["crowd"].process_frame(analyzed, camera_id=cam_id)
            for d in cr_det:
                alerts.append(f"[{cam_id}] 📢 {d['type']} ({d['confidence']}%)")
        except Exception:
            pass

    if cfg.get("face") and engines["face"] is not None:
        try:
            if hasattr(engines["face"], "process_frame_with_details"):
                analyzed, t_det = engines["face"].process_frame_with_details(analyzed)
                for t in t_det:
                    if t.get("status") == "MATCHED":
                        alerts.append(f"[{cam_id}] 🎯 TARGET: {t.get('name', 'MATCH')}")
            elif hasattr(engines["face"], "detect_and_draw"):
                analyzed, f_list = engines["face"].detect_and_draw(
                    analyzed, enabled=True
                )
                if f_list:
                    alerts.append(f"[{cam_id}] 👤 FACE DETECTED ({len(f_list)})")
        except Exception:
            pass

    if (
        cfg.get("alpr")
        and engines["alpr"] is not None
        and hasattr(engines["alpr"], "process_frame")
    ):
        try:
            analyzed, p_det = engines["alpr"].process_frame(analyzed)
            if isinstance(p_det, list):
                for p in p_det:
                    alerts.append(f"[{cam_id}] 🚗 PLATE: {p.get('plate', '')}")
            elif isinstance(p_det, dict) and p_det.get("plate"):
                alerts.append(f"[{cam_id}] 🚗 PLATE: {p_det.get('plate', '')}")
        except Exception:
            pass

    return analyzed, alerts


def show_dashboard() -> None:
    """داشبۆردی سەرەکیی APEX بە ڕووکاری Hikvision DVR Command Center."""
    _inject_dvr_styles()

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
            "🚪 چوونەدەرەوە (Logout)", width="stretch", key="btn_apex_logout"
        ):
            st.session_state.is_streaming = False
            st.session_state.authenticated = False
            st.session_state.logged_in = False
            st.rerun()

    if nav_tab == "🗄️ DATABASE & 4-STAGE ARCHIVE":
        if render_db_manager_view is not None:
            render_db_manager_view()
        else:
            st.warning("مۆدیولی db_manager_view بەردەست نییە.")
        return

    if nav_tab == "🗺️ TACTICAL GIS (CIA/FBI MODE)":
        if render_gis_intelligence_view is not None:
            render_gis_intelligence_view()
        else:
            st.warning("مۆدیولی gis_intelligence بەردەست نییە.")
        return

    if nav_tab == "🔬 FORENSICS & INVESTIGATION":
        if render_forensics_view is not None:
            render_forensics_view()
        else:
            st.warning("مۆدیولی forensics_view بەردەست نییە.")
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
        else:
            st.warning("مۆدیولی cyber_shield بەردەست نییە.")
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
                    [
                        "Use Camera Matrix Config",
                        "Webcam (Local 0)",
                        "Capture Card (Index 1)",
                        "Custom RTSP URL",
                    ],
                    key="dvr_stream_src_sel",
                    label_visibility="collapsed",
                )
                or "Use Camera Matrix Config"
            )
        override_source: Union[int, str, None] = None
        if stream_choice == "Webcam (Local 0)":
            override_source = 0
        elif stream_choice == "Capture Card (Index 1)":
            override_source = 1
        elif stream_choice == "Custom RTSP URL":
            override_source = str(
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
                    "▶ START LIVE DVR", width="stretch", key="btn_dvr_start"
                ):
                    st.session_state.is_streaming = True
                    st.rerun()
            else:
                if st.button(
                    "⏹ STOP LIVE DVR",
                    type="primary",
                    width="stretch",
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

        cam_boxes: Dict[str, Any] = {}
        if grid_mode == "1x1 Focus (CAM-01)":
            st.markdown(
                f"<div class='dvr-channel-bar'>🔴 CH-01 | {cam_matrix['CAM-01']['name']} | AI: {', '.join(_active_ai_tags('CAM-01'))}</div>",
                unsafe_allow_html=True,
            )
            cam_boxes["CAM-01"] = st.empty()
        else:
            g1, g2 = st.columns(2)
            with g1:
                st.markdown(
                    f"<div class='dvr-channel-bar'>🔴 CH-01 | {cam_matrix['CAM-01']['name']} | {', '.join(_active_ai_tags('CAM-01'))}</div>",
                    unsafe_allow_html=True,
                )
                cam_boxes["CAM-01"] = st.empty()
                st.markdown(
                    f"<div class='dvr-channel-bar'>🔴 CH-03 | {cam_matrix['CAM-03']['name']} | {', '.join(_active_ai_tags('CAM-03'))}</div>",
                    unsafe_allow_html=True,
                )
                cam_boxes["CAM-03"] = st.empty()
            with g2:
                st.markdown(
                    f"<div class='dvr-channel-bar'>🔴 CH-02 | {cam_matrix['CAM-02']['name']} | {', '.join(_active_ai_tags('CAM-02'))}</div>",
                    unsafe_allow_html=True,
                )
                cam_boxes["CAM-02"] = st.empty()
                st.markdown(
                    f"<div class='dvr-channel-bar'>🔴 CH-04 | {cam_matrix['CAM-04']['name']} | {', '.join(_active_ai_tags('CAM-04'))}</div>",
                    unsafe_allow_html=True,
                )
                cam_boxes["CAM-04"] = st.empty()

        if not st.session_state.is_streaming:
            for cid, box in cam_boxes.items():
                box.image(
                    _make_standby_frame(
                        cid, cam_matrix[cid]["name"], _active_ai_tags(cid)
                    ),
                    width="stretch",
                )

    with right_panel:
        with st.container(border=True):
            st.markdown("##### 🚨 LIVE AI THREAT FEED")
            live_feed_box = st.empty()
            live_feed_box.info("🟢 هەموو بزوێنەرەکان لە ئامادەباشیدان (100% Offline)")

        with st.container(border=True):
            st.markdown("##### 🤖 ACTIVE AI MODULES")
            st.markdown(
                f"{'🟢' if engines['fire'] else '🟡'} **Fire & Smoke AI:** {'READY' if engines['fire'] else 'STANDBY'}"
            )
            st.markdown(
                f"{'🟢' if engines['weapon'] else '🟡'} **Weapon & Gunfire AI:** {'READY' if engines['weapon'] else 'STANDBY'}"
            )
            st.markdown(
                f"{'🟢' if engines['crowd'] else '🟡'} **Crowd & Distress AI:** {'READY' if engines['crowd'] else 'STANDBY'}"
            )
            st.markdown(
                f"{'🟢' if (engines['face'] or engines['alpr']) else '🟡'} **Face ID & ALPR:** {'READY' if (engines['face'] or engines['alpr']) else 'STANDBY'}"
            )

    if st.session_state.is_streaming:
        if CameraBackend is None:
            st.error("فایلی cameras.py نەدۆزرایەوە.")
            return

        active_cids = list(cam_boxes.keys())
        streams_by_source: Dict[Union[int, str], Any] = {}
        channel_sources: Dict[str, Union[int, str]] = {}
        ai_workers: Dict[str, Any] = {}

        for cid in active_cids:
            src = (
                override_source
                if override_source is not None
                else cam_matrix[cid]["source"]
            )
            channel_sources[cid] = src
            if src not in streams_by_source:
                streams_by_source[src] = _open_camera_stream(
                    cid, src, str(cam_matrix[cid]["name"])
                )

            if AsyncAIWorkerBackend is not None:
                ch_cfg = dict(cam_matrix[cid])
                ai_workers[cid] = AsyncAIWorkerBackend(
                    cid,
                    lambda frm, c_id=cid, c_cfg=ch_cfg: _analyze_channel_frame(
                        frm, c_id, c_cfg, engines
                    ),
                )

        frame_idx = 0
        recent_alerts: List[str] = []

        try:
            while st.session_state.get("is_streaming", False):
                frames_by_source: Dict[Union[int, str], np.ndarray] = {}
                ai_frames_by_source: Dict[Union[int, str], np.ndarray] = {}

                for src, stream_obj in streams_by_source.items():
                    if stream_obj is None:
                        continue
                    raw = stream_obj.get_frame(copy=False)
                    if (
                        raw is not None
                        and isinstance(raw, np.ndarray)
                        and raw.size > 0
                    ):
                        frames_by_source[src] = raw
                        if hasattr(stream_obj, "get_ai_frame"):
                            ai_frm = stream_obj.get_ai_frame(max_width=640)
                            if ai_frm is not None:
                                ai_frames_by_source[src] = ai_frm

                if not frames_by_source:
                    time.sleep(0.02)
                    continue

                frame_idx += 1
                submit_ai_now = frame_idx % 3 == 0
                if get_internal_cpu is not None:
                    submit_ai_now = get_internal_cpu().should_process_frame(frame_idx)

                cycle_alerts: List[str] = []

                for cid in active_cids:
                    src = channel_sources[cid]
                    raw_frame = frames_by_source.get(src)
                    if raw_frame is None:
                        cam_boxes[cid].image(
                            _make_standby_frame(
                                cid, cam_matrix[cid]["name"], _active_ai_tags(cid)
                            ),
                            width="stretch",
                        )
                        continue

                    worker = ai_workers.get(cid)
                    if worker is not None:
                        if submit_ai_now:
                            ai_input = ai_frames_by_source.get(src, raw_frame)
                            worker.submit_frame(ai_input)

                        annotated_ai, ch_alerts = worker.get_latest_result(
                            max_age_sec=1.0
                        )
                        cycle_alerts.extend(ch_alerts)
                        display_bgr = (
                            annotated_ai if annotated_ai is not None else raw_frame
                        )
                    else:
                        if submit_ai_now:
                            display_bgr, ch_alerts = _analyze_channel_frame(
                                raw_frame, cid, cam_matrix[cid], engines
                            )
                            cycle_alerts.extend(ch_alerts)
                        else:
                            display_bgr = raw_frame

                    rgb_out = _cv2.cvtColor(display_bgr, _cv2.COLOR_BGR2RGB)
                    cam_boxes[cid].image(rgb_out, width="stretch")

                if cycle_alerts:
                    stamp = datetime.now().strftime("%H:%M:%S")
                    for alert_msg in cycle_alerts:
                        recent_alerts.insert(0, f"`{stamp}` {alert_msg}")
                    recent_alerts = recent_alerts[:12]
                    live_feed_box.error("\n\n".join(recent_alerts))

                time.sleep(0.025)
        finally:
            for worker in ai_workers.values():
                worker.stop()
            for stream_obj in streams_by_source.values():
                _close_camera_stream(stream_obj)


if __name__ == "__main__":
    st.set_page_config(
        page_title="APEX Security DVR",
        page_icon="🐉",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    show_dashboard()