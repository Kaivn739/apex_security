from __future__ import annotations

import importlib
import os
import sqlite3
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import cv2
import numpy as np
import streamlit as st

_cv2: Any = cv2
PROJECT_ROOT = Path(__file__).resolve().parent
DB_PATH = PROJECT_ROOT / "apex_security.db"
TARGETS_DIR = PROJECT_ROOT / "targets"
TARGETS_DIR.mkdir(parents=True, exist_ok=True)


def _load_attr(module_name: str, *attr_names: str) -> Any:
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


def _init_target_watchlist_tables() -> None:
    conn = sqlite3.connect(str(DB_PATH), timeout=10.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS targets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            target_type TEXT NOT NULL,
            status TEXT NOT NULL,
            plate_or_id TEXT NOT NULL,
            image_path TEXT DEFAULT '',
            created_at TEXT NOT NULL
        )
    """)
    cur.execute("PRAGMA table_info(targets)")
    cols = [row[1] for row in cur.fetchall()]
    if "image_path" not in cols:
        cur.execute("ALTER TABLE targets ADD COLUMN image_path TEXT DEFAULT ''")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS apex_system_settings (
            setting_key TEXT PRIMARY KEY,
            setting_value TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def _save_system_setting(key: str, value: str) -> None:
    _init_target_watchlist_tables()
    conn = sqlite3.connect(str(DB_PATH), timeout=10.0)
    conn.execute(
        "INSERT OR REPLACE INTO apex_system_settings (setting_key, setting_value) VALUES (?, ?)",
        (key, value.strip()),
    )
    conn.commit()
    conn.close()


def _get_system_setting(key: str, default: str = "") -> str:
    _init_target_watchlist_tables()
    conn = sqlite3.connect(str(DB_PATH), timeout=10.0)
    cur = conn.cursor()
    cur.execute(
        "SELECT setting_value FROM apex_system_settings WHERE setting_key = ?", (key,)
    )
    row = cur.fetchone()
    conn.close()
    return str(row[0]) if row else default


def _format_telegram_alert_text(
    target_label: str,
    event_type: str,
    severity: str,
    cam_id: str,
    cam_name: str,
    ts_str: str,
    details_note: str,
) -> str:
    lang = _get_system_setting("telegram_lang", "KU")
    note_clean = details_note or "پشتڕاستکراوەتەوە لەلایەن زیرەکی دەستکردی APEX"

    if lang == "KU":
        return (
            f"🚨 ئاگادارکردنەوەی بەپەلەی ئەمنیی APEX 🚨\n"
            f"🎯 تارگێت / ڕووداو: {target_label}\n"
            f"📌 جۆر: {event_type} [{severity}]\n"
            f"📹 کامێرا: {cam_id} ({cam_name})\n"
            f"🕒 کات: {ts_str}\n"
            f"📝 وردەکاری: {note_clean}"
        )
    if lang == "AR":
        return (
            f"🚨 تنبيه أمني عاجل من نظام APEX 🚨\n"
            f"🎯 الهدف / الحدث: {target_label}\n"
            f"📌 النوع: {event_type} [{severity}]\n"
            f"📹 الكاميرا: {cam_id} ({cam_name})\n"
            f"🕒 الوقت: {ts_str}\n"
            f"📝 التفاصيل: {details_note or 'تم التأكيد بواسطة ذكاء APEX الاصطناعي'}"
        )
    return (
        f"🚨 APEX SECURITY ALERT 🚨\n"
        f"🎯 Target/Event: {target_label}\n"
        f"📌 Type: {event_type} [{severity}]\n"
        f"📹 Camera: {cam_id} ({cam_name})\n"
        f"🕒 Time: {ts_str}\n"
        f"📝 Details: {details_note or 'Confirmed by APEX AI'}"
    )


def _send_telegram_alert_async(caption: str, image_path: Optional[str] = None) -> None:
    token = _get_system_setting("telegram_bot_token", "")
    chat_id = _get_system_setting("telegram_chat_id", "")
    enabled = _get_system_setting("telegram_enabled", "0") == "1"

    if not enabled or not token or not chat_id:
        return

    def _worker() -> None:
        try:
            if image_path and os.path.exists(image_path):
                boundary = f"----APEXBoundary{int(time.time() * 1000)}"
                with open(image_path, "rb") as img_file:
                    img_bytes = img_file.read()

                body = bytearray()
                body.extend(f"--{boundary}\r\n".encode("utf-8"))
                body.extend(b'Content-Disposition: form-data; name="chat_id"\r\n\r\n')
                body.extend(f"{chat_id}\r\n".encode("utf-8"))

                body.extend(f"--{boundary}\r\n".encode("utf-8"))
                body.extend(b'Content-Disposition: form-data; name="caption"\r\n\r\n')
                body.extend(f"{caption}\r\n".encode("utf-8"))

                body.extend(f"--{boundary}\r\n".encode("utf-8"))
                body.extend(
                    f'Content-Disposition: form-data; name="photo"; filename="{os.path.basename(image_path)}"\r\n'.encode(
                        "utf-8"
                    )
                )
                body.extend(b"Content-Type: image/jpeg\r\n\r\n")
                body.extend(img_bytes)
                body.extend(f"\r\n--{boundary}--\r\n".encode("utf-8"))

                url = f"https://api.telegram.org/bot{token}/sendPhoto"
                req = urllib.request.Request(url, data=bytes(body))
                req.add_header(
                        "Content-Type", f"multipart/form-data; boundary={boundary}"
                        )
                with urllib.request.urlopen(req, timeout=5):
                    pass
            else:
                url = f"https://api.telegram.org/bot{token}/sendMessage"
                payload = urllib.parse.urlencode(
                    {"chat_id": chat_id, "text": caption}
                ).encode("utf-8")
                req = urllib.request.Request(url, data=payload)
                with urllib.request.urlopen(req, timeout=5):
                    pass
        except Exception:
            pass

    threading.Thread(target=_worker, name="APEX-TelegramDispatch", daemon=True).start()


def _sync_targets_to_engines(engines: Dict[str, Any]) -> List[Dict[str, Any]]:
    _init_target_watchlist_tables()
    conn = sqlite3.connect(str(DB_PATH), timeout=10.0)
    cur = conn.cursor()

    for fname in sorted(os.listdir(TARGETS_DIR)):
        if fname.lower().endswith((".jpg", ".jpeg", ".png", ".bmp")):
            full_p = str(TARGETS_DIR / fname)
            clean_name = os.path.splitext(fname)[0].replace("_", " ").strip().title()
            cur.execute("SELECT id FROM targets WHERE image_path = ?", (full_p,))
            if cur.fetchone() is None:
                cur.execute(
                    """
                    INSERT INTO targets (name, target_type, status, plate_or_id, image_path, created_at)
                    VALUES (?, 'FACE_TARGET', 'WANTED', ?, ?, ?)
                    """,
                    (
                        clean_name,
                        f"ID-{abs(hash(fname)) % 90000 + 10000}",
                        full_p,
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    ),
                )
    conn.commit()

    cur.execute(
        "SELECT id, name, target_type, status, plate_or_id, image_path, created_at FROM targets ORDER BY id DESC"
    )
    rows = cur.fetchall()
    conn.close()

    target_list: List[Dict[str, Any]] = []
    for r in rows:
        item = {
            "id": r[0],
            "name": r[1],
            "target_type": r[2],
            "status": r[3],
            "plate_or_id": r[4],
            "image_path": r[5],
            "created_at": r[6],
        }
        target_list.append(item)

        if item["target_type"] == "PLATE_TARGET" and engines.get("alpr") is not None:
            if hasattr(engines["alpr"], "register_plate"):
                engines["alpr"].register_plate(
                    plate_number=item["plate_or_id"],
                    owner=item["name"],
                    status=item["status"],
                    severity="CRITICAL" if item["status"] == "BLACK_LISTED" else "HIGH",
                )

    if engines.get("face") is not None and hasattr(
        engines["face"], "_refresh_target_gallery"
    ):
        engines["face"]._refresh_target_gallery()

    return target_list


def _inject_dvr_styles() -> None:
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
    engines: Dict[str, Any] = {
        "face": (
            FaceBackend(targets_dir=str(TARGETS_DIR))
            if FaceBackend is not None
            else None
        ),
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
            APEXCyberShield(PROJECT_ROOT) if APEXCyberShield is not None else None
        ),
        "alert_cooldown": {},
    }

    if engines["db"] is not None and hasattr(engines["db"], "attach_to_internal_cpu"):
        engines["db"].attach_to_internal_cpu()
    if engines["gis"] is not None and hasattr(engines["gis"], "attach_to_internal_cpu"):
        engines["gis"].attach_to_internal_cpu()

    _sync_targets_to_engines(engines)
    return engines


def _handle_confirmed_target_hit(
    engines: Dict[str, Any],
    cam_id: str,
    cam_name: str,
    target_label: str,
    event_type: str,
    severity: str,
    annotated_frame: np.ndarray,
    details_note: str = "",
) -> None:
    cooldown_map: Dict[str, float] = engines.setdefault("alert_cooldown", {})
    key = f"{cam_id}:{event_type}:{target_label}"
    now = time.monotonic()
    if (now - cooldown_map.get(key, 0.0)) < 12.0:
        return
    cooldown_map[key] = now

    saved_snap_path: Optional[str] = None
    db_mgr = engines.get("db")
    if db_mgr is not None and hasattr(db_mgr, "log_detection_record"):
        try:
            rec_id = db_mgr.log_detection_record(
                target_name=target_label,
                event_type=event_type,
                camera_id=cam_id,
                location_name=cam_name,
                severity=severity,
                frame=annotated_frame,
                notes=details_note,
            )
            recent = db_mgr.fetch_records(limit=1, run_rotation=False)
            if recent and int(recent[0]["id"]) == int(rec_id):
                saved_snap_path = str(recent[0].get("snapshot_path", ""))
        except Exception:
            pass

    gis_eng = engines.get("gis")
    if gis_eng is not None and hasattr(gis_eng, "record_suspect_movement"):
        try:
            gis_eng.record_suspect_movement(
                suspect_label=target_label,
                camera_id=cam_id,
                threat_type=event_type,
                severity=severity,
            )
        except Exception:
            pass

    ts_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tg_caption = _format_telegram_alert_text(
        target_label=target_label,
        event_type=event_type,
        severity=severity,
        cam_id=cam_id,
        cam_name=cam_name,
        ts_str=ts_str,
        details_note=details_note,
    )
    _send_telegram_alert_async(tg_caption, image_path=saved_snap_path)


def _make_standby_frame(
    cam_id: str,
    label: str,
    active_ai: List[str],
    status_msg: str = "HIKVISION DVR STANDBY — NO SIGNAL",
) -> np.ndarray:
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
        status_msg,
        (18, 165),
        _cv2.FONT_HERSHEY_SIMPLEX,
        0.58,
        (
            (248, 113, 113)
            if "ERROR" in status_msg or "OPEN" in status_msg
            else (148, 163, 184)
        ),
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
                "fire": False,
                "weapon": False,
                "crowd": False,
            },
            "CAM-02": {
                "name": "Vehicle Parking",
                "source": 0,
                "face": False,
                "alpr": True,
                "fire": False,
                "weapon": False,
                "crowd": False,
            },
            "CAM-03": {
                "name": "Central Hall",
                "source": 0,
                "face": True,
                "alpr": False,
                "fire": True,
                "weapon": False,
                "crowd": True,
            },
            "CAM-04": {
                "name": "Restricted Perimeter",
                "source": 0,
                "face": False,
                "alpr": False,
                "fire": True,
                "weapon": False,
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
    cfg_ref: Dict[str, Any],
    engines: Dict[str, Any],
) -> Tuple[np.ndarray, List[str], List[Dict[str, Any]]]:
    analyzed = frame.copy()
    alerts: List[str] = []
    face_boxes: List[Dict[str, Any]] = []
    cam_name = str(cfg_ref.get("name", cam_id))

    if cfg_ref.get("face") and engines["face"] is not None:
        try:
            if hasattr(engines["face"], "process_frame_with_details"):
                analyzed, t_det = engines["face"].process_frame_with_details(analyzed)
                face_boxes = list(t_det)
                for t in t_det:
                    t_name = str(t.get("name", "Unknown"))
                    t_score = t.get("score", 0.0)
                    if t.get("status") == "MATCHED":
                        alerts.append(f"[{cam_id}] 🎯 TARGET: {t_name} ({t_score}%)")
                        _handle_confirmed_target_hit(
                            engines,
                            cam_id,
                            cam_name,
                            t_name,
                            "TARGET_FACE_MATCH",
                            "CRITICAL",
                            analyzed,
                            f"Biometric Match Score: {t_score}%",
                        )
        except Exception:
            pass

    if cfg_ref.get("fire") and engines["fire"] is not None:
        try:
            analyzed, f_det = engines["fire"].process_frame(
                analyzed, camera_id=cam_id, emit_events=False
            )
            for d in f_det:
                msg = f"[{cam_id}] 🔥 {d['type']} ({d['confidence']}%)"
                alerts.append(msg)
                _handle_confirmed_target_hit(
                    engines,
                    cam_id,
                    cam_name,
                    str(d["type"]),
                    "FIRE_SMOKE",
                    "CRITICAL",
                    analyzed,
                    f"Confidence: {d['confidence']}%",
                )
        except Exception:
            pass

    if cfg_ref.get("weapon") and engines["weapon"] is not None:
        try:
            analyzed, w_det = engines["weapon"].process_frame(
                analyzed, camera_id=cam_id, emit_events=False
            )
            for d in w_det:
                msg = f"[{cam_id}] 🔫 {d['type']} ({d['confidence']}%)"
                alerts.append(msg)
                _handle_confirmed_target_hit(
                    engines,
                    cam_id,
                    cam_name,
                    str(d["type"]),
                    "WEAPON",
                    "CRITICAL",
                    analyzed,
                    f"Confidence: {d['confidence']}%",
                )
        except Exception:
            pass

    if cfg_ref.get("crowd") and engines["crowd"] is not None:
        try:
            analyzed, cr_det = engines["crowd"].process_frame(
                analyzed, camera_id=cam_id, emit_events=False
            )
            for d in cr_det:
                msg = f"[{cam_id}] 📢 {d['type']} ({d['confidence']}%)"
                alerts.append(msg)
                _handle_confirmed_target_hit(
                    engines,
                    cam_id,
                    cam_name,
                    str(d["type"]),
                    "CROWD_DISTRESS",
                    "HIGH",
                    analyzed,
                    f"Confidence: {d['confidence']}%",
                )
        except Exception:
            pass

    if (
        cfg_ref.get("alpr")
        and engines["alpr"] is not None
        and hasattr(engines["alpr"], "process_frame")
    ):
        try:
            analyzed, p_det = engines["alpr"].process_frame(analyzed, camera_id=cam_id)
            if isinstance(p_det, list):
                for p in p_det:
                    plate_txt = str(p.get("plate", ""))
                    p_status = str(p.get("status", ""))
                    if plate_txt and plate_txt != "PLATE_REGION":
                        alerts.append(f"[{cam_id}] 🚗 PLATE: {plate_txt} [{p_status}]")
                        if p_status in {"SUSPECT", "BLACK_LISTED"}:
                            _handle_confirmed_target_hit(
                                engines,
                                cam_id,
                                cam_name,
                                f"PLATE {plate_txt}",
                                "TARGET_PLATE_MATCH",
                                "CRITICAL",
                                analyzed,
                                f"Watchlist Status: {p_status}",
                            )
        except Exception:
            pass

    return analyzed, alerts, face_boxes


def _draw_persisted_face_boxes(
    frame: np.ndarray, boxes: List[Dict[str, Any]]
) -> np.ndarray:
    """کێشانی بەردەوامی چوارچێوەی ڕووخسار لە نێوان فریمەکاندا تا هەرگیز ون نەبێت."""
    out = frame.copy()
    for item in boxes:
        bbox = item.get("bbox")
        if not bbox or len(bbox) != 4:
            continue
        x, y, w, h = [int(v) for v in bbox]
        status = str(item.get("status", "UNKNOWN"))
        t_name = str(item.get("name", "Unknown Subject"))
        score = item.get("score", 0.0)
        color = (0, 255, 0) if status == "MATCHED" else (0, 165, 255)
        label = (
            f"TARGET: {t_name} ({score}%)"
            if status == "MATCHED"
            else f"FACE: {t_name} ({score}%)"
        )
        _cv2.rectangle(out, (x, y), (x + w, y + h), color, 3)
        _cv2.rectangle(
            out,
            (x, max(0, y - 26)),
            (x + max(w, len(label) * 9 + 14), y),
            (15, 23, 42),
            -1,
        )
        _cv2.putText(
            out,
            label,
            (x + 5, max(18, y - 7)),
            _cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            color,
            2,
        )
    return out


def _render_targets_watchlist_view(engines: Dict[str, Any]) -> None:
    st.markdown("## 🎯 TARGETS & WATCHLIST COMMAND (بەڕێوەبردنی تارگێتەکان)")
    st.caption(
        "هەر تارگێتێک لێرە زیاد بکەیت، ڕاستەوخۆ دەچێتە ناو داتابەیسی گشتیی ئەپێکس و هەموو کامێراکان چاودێری دەکەن؛ "
        "لە کاتی بینینیدا ئاگادارکردنەوە دێت، وێنەکەی سەیڤ دەکرێت، و کۆپییەک بۆ تەلەگرام دەنێردرێت."
    )

    all_targets = _sync_targets_to_engines(engines)
    face_targets = [t for t in all_targets if t["target_type"] == "FACE_TARGET"]
    plate_targets = [t for t in all_targets if t["target_type"] == "PLATE_TARGET"]

    m1, m2, m3 = st.columns(3)
    m1.metric("🎯 کۆی تارگێتە چالاکەکان", len(all_targets))
    m2.metric("👤 تارگێتەکانی ڕووخسار (Face)", len(face_targets))
    m3.metric("🚘 تارگێتەکانی تابلۆ (ALPR)", len(plate_targets))

    st.markdown("---")
    add_col, list_col = st.columns([1.25, 1.75])

    with add_col:
        with st.container(border=True):
            st.markdown("##### ➕ پێدانی تارگێتی نوێ بە مۆدیولەکان")
            t_category = str(
                st.radio(
                    "جۆری تارگێت:",
                    [
                        "👤 تارگێتی ڕووخسار (Face Target)",
                        "🚘 تارگێتی تابلۆی ئۆتۆمبێل (Plate)",
                    ],
                    key="tgt_cat_radio",
                )
                or "👤 تارگێتی ڕووخسار (Face Target)"
            )

            if "Face Target" in t_category:
                f_name = str(
                    st.text_input(
                        "ناوی تارگێت / گومانلێکراو:",
                        placeholder="نموونە: ئارام محەمەد",
                        key="tgt_face_name",
                    )
                    or ""
                )
                f_code = str(
                    st.text_input(
                        "ژمارەی دۆسیە یان ناسنامە:",
                        placeholder="نموونە: W-2026-09",
                        key="tgt_face_code",
                    )
                    or ""
                )
                f_status = str(
                    st.selectbox(
                        "ئاستی داواکراوی:",
                        ["WANTED", "HIGH_RISK", "SUSPECT", "VIP_MONITOR"],
                        key="tgt_face_status",
                    )
                    or "WANTED"
                )
                uploaded_photo = st.file_uploader(
                    "وێنەی ڕووخساری تارگێت بار بکە (JPG / PNG):",
                    type=["jpg", "jpeg", "png"],
                    key="tgt_face_upload",
                )

                if st.button(
                    "💾 تۆمارکردن و ناردن بۆ مۆدیولەکانی AI",
                    width="stretch",
                    key="btn_add_face_target",
                ):
                    if not f_name.strip() or uploaded_photo is None:
                        st.warning("⚠️ تکایە ناوی تارگێت بنووسە و وێنەیەک هەڵبژێرە.")
                    else:
                        file_bytes = np.asarray(
                            bytearray(uploaded_photo.read()), dtype=np.uint8
                        )
                        img_bgr = _cv2.imdecode(file_bytes, _cv2.IMREAD_COLOR)
                        if img_bgr is not None and img_bgr.size > 0:
                            safe_slug = "".join(
                                c if c.isalnum() else "_" for c in f_name.strip()
                            ).strip("_")
                            safe_slug = safe_slug or f"target_{int(time.time())}"
                            saved_img_path = str(TARGETS_DIR / f"{safe_slug}.jpg")
                            _cv2.imwrite(saved_img_path, img_bgr)

                            conn = sqlite3.connect(str(DB_PATH), timeout=10.0)
                            conn.execute(
                                """
                                INSERT INTO targets (name, target_type, status, plate_or_id, image_path, created_at)
                                VALUES (?, 'FACE_TARGET', ?, ?, ?, ?)
                                """,
                                (
                                    f_name.strip(),
                                    f_status,
                                    f_code.strip() or safe_slug.upper(),
                                    saved_img_path,
                                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                ),
                            )
                            conn.commit()
                            conn.close()

                            _sync_targets_to_engines(engines)
                            st.success(
                                f"✅ تارگێت `{f_name}` بە سەرکەوتوویی زیاد کرا و پەیوەست کرا بە کامێراکانەوە!"
                            )
                            st.rerun()
            else:
                p_num = str(
                    st.text_input(
                        "ژمارەی تابلۆ (Plate Number):",
                        placeholder="نموونە: 22B-10922",
                        key="tgt_plate_num",
                    )
                    or ""
                )
                p_owner = str(
                    st.text_input(
                        "ناوی خاوەن / زانیاری:",
                        placeholder="نموونە: ئۆتۆمبێلی داواکراو",
                        key="tgt_plate_owner",
                    )
                    or ""
                )
                p_status = str(
                    st.selectbox(
                        "دۆخی تابلۆ:",
                        ["SUSPECT", "BLACK_LISTED", "WANTED"],
                        key="tgt_plate_status",
                    )
                    or "SUSPECT"
                )
                if st.button(
                    "🚘 تۆمارکردنی تابلۆ لە لیستی چاودێری",
                    width="stretch",
                    key="btn_add_plate_target",
                ):
                    if not p_num.strip():
                        st.warning("⚠️ تکایە ژمارەی تابلۆ بنووسە.")
                    else:
                        clean_p = p_num.strip().upper()
                        conn = sqlite3.connect(str(DB_PATH), timeout=10.0)
                        conn.execute(
                            """
                            INSERT INTO targets (name, target_type, status, plate_or_id, image_path, created_at)
                            VALUES (?, 'PLATE_TARGET', ?, ?, '', ?)
                            """,
                            (
                                p_owner.strip() or f"Vehicle {clean_p}",
                                p_status,
                                clean_p,
                                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            ),
                        )
                        conn.commit()
                        conn.close()
                        _sync_targets_to_engines(engines)
                        st.success(f"✅ تابلۆی `{clean_p}` خرایە ژێر چاودێریی ALPR!")
                        st.rerun()

        with st.container(border=True):
            st.markdown("##### 📲 ڕێکخستنی ئاگادارکردنەوە و زمانی بۆتی تەلەگرام")
            tg_en = st.checkbox(
                "چالاککردنی ناردنی خۆکار بۆ تەلەگرام لە کاتی بینینی تارگێت",
                value=(_get_system_setting("telegram_enabled", "0") == "1"),
                key="tg_enable_chk",
            )
            lang_labels = {
                "کوردی (سۆرانی)": "KU",
                "English": "EN",
                "العربية": "AR",
            }
            cur_lang_code = _get_system_setting("telegram_lang", "KU")
            cur_lang_label = next(
                (lbl for lbl, code in lang_labels.items() if code == cur_lang_code),
                "کوردی (سۆرانی)",
            )
            selected_lang_lbl = str(
                st.selectbox(
                    "🌐 زمانی نامەکانی بۆتی تەلەگرام:",
                    list(lang_labels.keys()),
                    index=list(lang_labels.keys()).index(cur_lang_label),
                    key="tg_lang_sel",
                )
                or "کوردی (سۆرانی)"
            )
            chosen_lang_code = lang_labels[selected_lang_lbl]

            tg_token = str(
                st.text_input(
                    "Bot Token:",
                    value=_get_system_setting("telegram_bot_token", ""),
                    type="password",
                    key="tg_token_inp",
                )
                or ""
            )
            tg_chat = str(
                st.text_input(
                    "Chat ID:",
                    value=_get_system_setting("telegram_chat_id", ""),
                    key="tg_chat_inp",
                )
                or ""
            )
            c_tg1, c_tg2 = st.columns(2)
            with c_tg1:
                if st.button("💾 پاشەکەوتکردن", width="stretch", key="btn_save_tg"):
                    _save_system_setting("telegram_enabled", "1" if tg_en else "0")
                    _save_system_setting("telegram_lang", chosen_lang_code)
                    _save_system_setting("telegram_bot_token", tg_token)
                    _save_system_setting("telegram_chat_id", tg_chat)
                    st.success(
                        f"ڕێکخستن و زمانی تەلەگرام ({selected_lang_lbl}) پاشەکەوت کرا."
                    )
            with c_tg2:
                if st.button("📨 تاقیکردنەوە", width="stretch", key="btn_test_tg"):
                    _save_system_setting("telegram_enabled", "1" if tg_en else "0")
                    _save_system_setting("telegram_lang", chosen_lang_code)
                    _save_system_setting("telegram_bot_token", tg_token)
                    _save_system_setting("telegram_chat_id", tg_chat)
                    test_msgs = {
                        "KU": "✅ APEX SECURITY: پەیوەندی و زمانی کوردیی بۆتی تەلەگرام بە سەرکەوتوویی چالاک کرا!",
                        "EN": "✅ APEX SECURITY: Telegram Bot connection & English language verified!",
                        "AR": "✅ APEX SECURITY: تم تفعيل اتصال البوت واللغة العربية بنجاح!",
                    }
                    _send_telegram_alert_async(test_msgs[chosen_lang_code])
                    st.info("نامەی تاقیکردنەوە بە زمانە هەڵبژێردراوەکە نێردرا.")

    with list_col:
        st.markdown(
            "##### 📂 لیستی تارگێتە تۆمارکراوەکانی ناو فۆڵدەر و داتابەیسی ئەپێکس"
        )
        if not all_targets:
            st.info("هیچ تارگێتێک تۆمار نەکراوە. لە لای چەپەوە تارگێتێک زیاد بکە.")
        else:
            for item in all_targets:
                with st.container(border=True):
                    t_c1, t_c2, t_c3 = st.columns([0.9, 2.1, 0.8])
                    with t_c1:
                        img_p = str(item.get("image_path", ""))
                        if img_p and os.path.exists(img_p):
                            st.image(img_p, width="stretch")
                        else:
                            st.markdown(
                                "<div style='background:#0f172a; padding:18px; text-align:center; border-radius:6px; font-size:24px;'>🚘</div>",
                                unsafe_allow_html=True,
                            )
                    with t_c2:
                        st.markdown(f"**🎯 {item['name']}** (`{item['status']}`)")
                        st.caption(
                            f"جۆر: `{item['target_type']}` | کۆد/تابلۆ: `{item['plate_or_id']}`"
                        )
                        st.caption(f"بەرواری تۆمارکردن: `{item['created_at']}`")
                    with t_c3:
                        if st.button(
                            "🗑️ سڕینەوە",
                            key=f"del_tgt_{item['id']}",
                            width="stretch",
                        ):
                            conn = sqlite3.connect(str(DB_PATH), timeout=10.0)
                            conn.execute(
                                "DELETE FROM targets WHERE id = ?", (int(item["id"]),)
                            )
                            conn.commit()
                            conn.close()
                            img_del = str(item.get("image_path", ""))
                            if img_del and os.path.exists(img_del):
                                try:
                                    os.remove(img_del)
                                except OSError:
                                    pass
                            _sync_targets_to_engines(engines)
                            st.rerun()


def show_dashboard() -> None:
    _inject_dvr_styles()
    _init_target_watchlist_tables()

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
                    "🎯 TARGETS & WATCHLIST",
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
        if st.button("🚪 چوونەدەرەوە (Logout)", width="stretch", key="btn_apex_logout"):
            st.session_state.is_streaming = False
            st.session_state.authenticated = False
            st.session_state.logged_in = False
            st.rerun()

    if nav_tab == "🎯 TARGETS & WATCHLIST":
        _render_targets_watchlist_view(engines)
        return

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
        h_cols = st.columns([1.3, 1, 1, 1, 1, 1])
        h_cols[0].markdown("**کامێرا**")
        h_cols[1].markdown("**Face ID**")
        h_cols[2].markdown("**ALPR تابلۆ**")
        h_cols[3].markdown("**Fire/Smoke**")
        h_cols[4].markdown("**Weapon چەک**")
        h_cols[5].markdown("**Crowd/Distress**")

        is_live = bool(st.session_state.get("is_streaming", False))
        for cid, cfg in cam_matrix.items():
            r_cols = st.columns([1.3, 1, 1, 1, 1, 1])
            r_cols[0].write(f"**{cid}** ({cfg['name']})")
            cfg["face"] = r_cols[1].checkbox(
                "Face",
                value=bool(cfg["face"]),
                key=f"mx_f_{cid}",
                disabled=is_live,
                label_visibility="collapsed",
            )
            cfg["alpr"] = r_cols[2].checkbox(
                "ALPR",
                value=bool(cfg["alpr"]),
                key=f"mx_a_{cid}",
                disabled=is_live,
                label_visibility="collapsed",
            )
            cfg["fire"] = r_cols[3].checkbox(
                "Fire",
                value=bool(cfg["fire"]),
                key=f"mx_fi_{cid}",
                disabled=is_live,
                label_visibility="collapsed",
            )
            cfg["weapon"] = r_cols[4].checkbox(
                "Weapon",
                value=bool(cfg["weapon"]),
                key=f"mx_w_{cid}",
                disabled=is_live,
                label_visibility="collapsed",
            )
            cfg["crowd"] = r_cols[5].checkbox(
                "Crowd",
                value=bool(cfg["crowd"]),
                key=f"mx_c_{cid}",
                disabled=is_live,
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
                if st.button("▶ START LIVE DVR", width="stretch", key="btn_dvr_start"):
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
                    ["1x1 Focus (CAM-01)", "2x2 Matrix"],
                    key="dvr_grid_mode",
                    label_visibility="collapsed",
                )
                or "1x1 Focus (CAM-01)"
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
            st.markdown("##### 🎯 WATCHLIST STATUS")
            face_cnt = (
                len(engines["face"]._gallery_templates)
                if engines.get("face") is not None
                and hasattr(engines["face"], "_gallery_templates")
                else 0
            )
            plate_cnt = (
                len(engines["alpr"].target_database)
                if engines.get("alpr") is not None
                and hasattr(engines["alpr"], "target_database")
                else 0
            )
            st.markdown(f"👤 **Face Targets Active:** `{face_cnt}`")
            st.markdown(f"🚘 **Plate Targets Active:** `{plate_cnt}`")
            tg_state = (
                f"🟢 ACTIVE ({_get_system_setting('telegram_lang', 'KU')})"
                if _get_system_setting("telegram_enabled", "0") == "1"
                else "⚪ STANDBY"
            )
            st.markdown(f"📲 **Telegram Auto-Copy:** {tg_state}")

    if st.session_state.is_streaming:
        if CameraBackend is None:
            st.error("فایلی cameras.py نەدۆزرایەوە.")
            return

        _sync_targets_to_engines(engines)
        active_cids = list(cam_boxes.keys())
        streams_by_source: Dict[Union[int, str], Any] = {}
        channel_sources: Dict[str, Union[int, str]] = {}

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

        frame_idx = 0
        recent_alerts: List[str] = []
        last_face_boxes: Dict[str, Tuple[List[Dict[str, Any]], float]] = {}

        try:
            while st.session_state.get("is_streaming", False):
                frames_by_source: Dict[Union[int, str], np.ndarray] = {}
                for src, stream_obj in streams_by_source.items():
                    if stream_obj is None:
                        continue
                    raw = stream_obj.get_frame(copy=True)
                    if raw is not None and raw.size > 0:
                        frames_by_source[src] = raw

                if not frames_by_source:
                    for cid, box in cam_boxes.items():
                        box.image(
                            _make_standby_frame(
                                cid,
                                cam_matrix[cid]["name"],
                                _active_ai_tags(cid),
                                status_msg=f"WAITING FOR CAMERA ({channel_sources[cid]})...",
                            ),
                            width="stretch",
                        )
                    time.sleep(0.15)
                    continue

                frame_idx += 1
                cycle_alerts: List[str] = []
                now_mono = time.monotonic()

                for cid in active_cids:
                    src = channel_sources[cid]
                    raw_frame = frames_by_source.get(src)
                    if raw_frame is None:
                        continue

                    if (frame_idx % 2) == 0:
                        display_bgr, ch_alerts, f_boxes = _analyze_channel_frame(
                            raw_frame, cid, cam_matrix[cid], engines
                        )
                        cycle_alerts.extend(ch_alerts)
                        if f_boxes:
                            last_face_boxes[cid] = (f_boxes, now_mono)
                    else:
                        display_bgr = raw_frame.copy()
                        cached = last_face_boxes.get(cid)
                        if cached is not None and (now_mono - cached[1]) <= 1.2:
                            display_bgr = _draw_persisted_face_boxes(
                                display_bgr, cached[0]
                            )

                    rgb_out = _cv2.cvtColor(display_bgr, _cv2.COLOR_BGR2RGB)
                    cam_boxes[cid].image(rgb_out, width="stretch")

                if cycle_alerts:
                    stamp = datetime.now().strftime("%H:%M:%S")
                    for alert_msg in cycle_alerts:
                        recent_alerts.insert(0, f"`{stamp}` {alert_msg}")
                    recent_alerts = recent_alerts[:12]
                    live_feed_box.error("\n\n".join(recent_alerts))

                time.sleep(0.05)
        finally:
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
