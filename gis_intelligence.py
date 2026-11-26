from __future__ import annotations

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import cv2
import numpy as np

_cv2: Any = cv2

try:
    import streamlit as st
except ImportError:
    st = None  # type: ignore[assignment]

try:
    from apex_internal_core import get_internal_cpu
except ImportError:
    get_internal_cpu = None  # type: ignore[assignment]


class APEXGISIntelligenceEngine:
    """
    مۆدیۆلی لۆکەیشنی زیرەکی ئاستی CIA/FBI (100% Offline Tactical GIS):
    - نەخشەی تاکتیکیی ناوخۆیی بێ ئینتەرنێت (سفر پەیوەندی بە هەورەوە).
    - پیشاندانی شوێنی هەموو کامێرا کاراکان، گۆشەی بینین، و دۆخی سیکیوریتی.
    - کێشانی هێڵی جوڵەی تاوانبار و گومانلێکراو لە نێوان کامێراکاندا (Movement Vector Trail).
    """

    def __init__(self) -> None:
        self.project_root: Path = Path(__file__).resolve().parent
        self.state_file: Path = (
            self.project_root / ".apex_shield_vault" / "gis_tactical_state.json"
        )
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.cameras: Dict[str, Dict[str, Any]] = {}
        self.suspect_tracks: List[Dict[str, Any]] = []
        self._recent_track_guard: Dict[str, float] = {}
        self._load_or_seed_state()

    def _load_or_seed_state(self) -> None:
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.cameras = data.get("cameras", {})
                self.suspect_tracks = data.get("suspect_tracks", [])
                if self.cameras:
                    return
            except Exception:
                pass

        self.cameras = {
            "CAM-01": {
                "name": "دەروازەی سەرەکی (North Gate)",
                "x": 180,
                "y": 130,
                "lat": 36.1911,
                "lon": 44.0091,
                "status": "ACTIVE",
            },
            "CAM-02": {
                "name": "گۆڕەپانی ناوەڕاست (Central Plaza)",
                "x": 420,
                "y": 210,
                "lat": 36.1924,
                "lon": 44.0115,
                "status": "ACTIVE",
            },
            "CAM-03": {
                "name": "شەقامی ڕۆژهەڵات (East Avenue)",
                "x": 650,
                "y": 150,
                "lat": 36.1938,
                "lon": 44.0142,
                "status": "ACTIVE",
            },
            "CAM-04": {
                "name": "پارکی ئۆتۆمبێل (South Parking)",
                "x": 310,
                "y": 360,
                "lat": 36.1895,
                "lon": 44.0102,
                "status": "ACTIVE",
            },
            "CAM-05": {
                "name": "دەرچوونی ڕۆژئاوا (West Exit)",
                "x": 580,
                "y": 380,
                "lat": 36.1902,
                "lon": 44.0136,
                "status": "ACTIVE",
            },
        }
        self.suspect_tracks = []
        self._save_state()

    def _save_state(self) -> None:
        tmp_path = self.state_file.with_suffix(".json.tmp")
        try:
            payload = {
                "updated_at": datetime.now().isoformat(),
                "cameras": self.cameras,
                "suspect_tracks": self.suspect_tracks[-60:],
            }
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, self.state_file)
        except Exception:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass

    def register_camera_node(
        self,
        camera_id: str,
        name: str,
        x: int,
        y: int,
        lat: float = 36.1900,
        lon: float = 44.0100,
        status: str = "ACTIVE",
    ) -> None:
        self.cameras[camera_id] = {
            "name": str(name),
            "x": int(max(40, min(760, x))),
            "y": int(max(40, min(440, y))),
            "lat": float(lat),
            "lon": float(lon),
            "status": str(status).upper(),
        }
        self._save_state()

    def record_suspect_movement(
        self,
        suspect_label: str,
        camera_id: str,
        threat_type: str = "TARGET_DETECTED",
        severity: str = "HIGH",
    ) -> Dict[str, Any]:
        """تۆمارکردنی جوڵەی تاوانبار یان گومانلێکراو لەسەر نەخشەکە."""
        cam = self.cameras.get(camera_id)
        if cam is None:
            idx = len(self.cameras) + 1
            self.register_camera_node(
                camera_id,
                f"Node-{camera_id}",
                120 + (idx * 90) % 600,
                120 + (idx * 70) % 280,
            )
            cam = self.cameras[camera_id]

        cam["status"] = "ALERT" if severity in ("HIGH", "CRITICAL") else "ACTIVE"
        entry = {
            "suspect": str(suspect_label),
            "camera_id": str(camera_id),
            "zone_name": str(cam["name"]),
            "x": int(cam["x"]),
            "y": int(cam["y"]),
            "lat": float(cam["lat"]),
            "lon": float(cam["lon"]),
            "threat_type": str(threat_type),
            "severity": str(severity).upper(),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.suspect_tracks.append(entry)
        self._save_state()
        return entry

    def reset_camera_alerts(self) -> None:
        """گەڕاندنەوەی دۆخی هەموو کامێراکان بۆ ACTIVE دوای پشکنین."""
        for cam in self.cameras.values():
            cam["status"] = "ACTIVE"
        self._save_state()

    def render_tactical_map(self, width: int = 800, height: int = 480) -> np.ndarray:
        """کێشانی نەخشەی تاکتیکیی ئاستی CIA/FBI بە ١٠٠٪ ئۆفلاین."""
        canvas = np.zeros((int(height), int(width), 3), dtype=np.uint8)
        canvas[:] = (14, 19, 28)

        for gx in range(0, int(width), 50):
            _cv2.line(canvas, (gx, 0), (gx, int(height)), (26, 36, 52), 1)
        for gy in range(0, int(height), 50):
            _cv2.line(canvas, (0, gy), (int(width), gy), (26, 36, 52), 1)

        _cv2.line(canvas, (80, 130), (720, 150), (45, 62, 85), 6)
        _cv2.line(canvas, (180, 130), (420, 210), (45, 62, 85), 5)
        _cv2.line(canvas, (420, 210), (650, 150), (45, 62, 85), 5)
        _cv2.line(canvas, (310, 360), (580, 380), (45, 62, 85), 5)
        _cv2.line(canvas, (420, 210), (310, 360), (45, 62, 85), 4)

        recent_tracks = self.suspect_tracks[-10:]
        for idx in range(1, len(recent_tracks)):
            p1 = (int(recent_tracks[idx - 1]["x"]), int(recent_tracks[idx - 1]["y"]))
            p2 = (int(recent_tracks[idx]["x"]), int(recent_tracks[idx]["y"]))
            _cv2.line(canvas, p1, p2, (0, 60, 255), 3)
            _cv2.circle(canvas, p2, 6, (0, 140, 255), -1)

        for cam_id, info in self.cameras.items():
            cx = int(info["x"])
            cy = int(info["y"])
            is_alert = str(info.get("status", "ACTIVE")) == "ALERT"
            node_color: Tuple[int, int, int] = (
                (0, 0, 255) if is_alert else (0, 230, 140)
            )

            _cv2.circle(canvas, (cx, cy), 34, (35, 55, 75), 1)
            _cv2.circle(canvas, (cx, cy), 11, node_color, -1)
            _cv2.circle(canvas, (cx, cy), 15, (255, 255, 255), 1)
            _cv2.putText(
                canvas,
                f"{cam_id} [{info.get('status', 'ACTIVE')}]",
                (cx - 38, cy - 20),
                _cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                node_color,
                1,
            )

        if recent_tracks:
            last = recent_tracks[-1]
            lx, ly = int(last["x"]), int(last["y"])
            _cv2.circle(canvas, (lx, ly), 22, (0, 0, 255), 2)
            _cv2.putText(
                canvas,
                f"TARGET: {last['suspect']} ({last['camera_id']})",
                (max(12, lx - 75), min(int(height) - 16, ly + 36)),
                _cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 120, 255),
                2,
            )

        _cv2.rectangle(canvas, (0, 0), (int(width), 34), (10, 14, 22), -1)
        _cv2.putText(
            canvas,
            "APEX TACTICAL GIS INTELLIGENCE | 100% OFFLINE TRACKING",
            (14, 23),
            _cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (0, 220, 180),
            1,
        )
        return canvas

    def attach_to_internal_cpu(self) -> None:
        """بەستنەوەی خۆکار بە CPU ناوخۆیی لەگەڵ پارێزگاری دژی نووسینی دووبارەی خێرا."""
        if get_internal_cpu is None:
            return

        def _on_event(ev: Any) -> None:
            cam_id = str(getattr(ev, "camera_id", "CAM-01"))
            ev_type = str(getattr(ev, "event_type", "ALERT"))
            guard_key = f"{cam_id}:{ev_type}"
            now = time.monotonic()
            if (now - self._recent_track_guard.get(guard_key, 0.0)) < 6.0:
                return
            self._recent_track_guard[guard_key] = now

            self.record_suspect_movement(
                suspect_label=str(getattr(ev, "title", "SUSPECT")),
                camera_id=cam_id,
                threat_type=ev_type,
                severity=str(getattr(ev, "severity", "HIGH")),
            )

        get_internal_cpu().register_event_listener(_on_event)


def render_gis_intelligence_view() -> None:
    """ڕووکاری تابی لۆکەیشنی ئاستی CIA/FBI لە داشبۆردی APEX."""
    if st is None:
        return

    gis = APEXGISIntelligenceEngine()
    st.markdown("## 🗺️ APEX TACTICAL GIS & SUSPECT TRACKING (CIA/FBI MODE)")

    map_col, ctrl_col = st.columns([2.2, 1.1])
    with map_col:
        tactical_bgr = gis.render_tactical_map(width=820, height=480)
        tactical_rgb = _cv2.cvtColor(tactical_bgr, _cv2.COLOR_BGR2RGB)
        st.image(tactical_rgb, width="stretch")

    with ctrl_col:
        st.markdown("##### 📡 دۆخی کامێرا و خاڵەکان")
        for cid, cinfo in gis.cameras.items():
            badge = "🔴" if cinfo["status"] == "ALERT" else "🟢"
            st.write(
                f"{badge} **{cid}**: {cinfo['name']} (`{cinfo['lat']}, {cinfo['lon']}`)"
            )

        if st.button("🔄 سڕینەوەی ئاگادارییە سوورەکانی سەر نەخشە", key="gis_reset_alerts"):
            gis.reset_camera_alerts()
            st.rerun()

        st.markdown("---")
        st.markdown("##### 🎯 دیاریکردنی شوێنی گومانلێکراو")
        sus_name = str(
            st.text_input("ناوی تارگێت یان گومانلێکراو:", key="gis_sus_name") or ""
        )
        sus_cam = str(
            st.selectbox("کامێرای بینراو:", list(gis.cameras.keys()), key="gis_sus_cam")
            or "CAM-01"
        )
        if st.button("📍 تۆمارکردنی جوڵە لەسەر نەخشە", key="gis_add_track_btn"):
            if sus_name.strip():
                gis.record_suspect_movement(
                    sus_name.strip(), sus_cam, "MANUAL_TRACK", "CRITICAL"
                )
                st.success(f"شوێنی `{sus_name}` لەسەر {sus_cam} دیاری کرا.")
                st.rerun()

    if gis.suspect_tracks:
        st.markdown("##### 🧭 زنجیرەی جوڵەی دۆزراوەکان")
        for tr in reversed(gis.suspect_tracks[-8:]):
            st.caption(
                f"🕒 `{tr['timestamp']}` | 🎯 **{tr['suspect']}** -> 📍 {tr['zone_name']} ({tr['camera_id']}) [{tr['threat_type']}]"
            )


if __name__ == "__main__":
    gis_engine = APEXGISIntelligenceEngine()
    gis_engine.record_suspect_movement("SUSPECT_ALPHA", "CAM-01", "FACE_MATCH", "HIGH")
    gis_engine.record_suspect_movement("SUSPECT_ALPHA", "CAM-02", "WEAPON", "CRITICAL")
    map_img = gis_engine.render_tactical_map()
    print(
        f"[GIS INTELLIGENCE] Offline Ready | Map Shape: {map_img.shape} | Tracks: {len(gis_engine.suspect_tracks)}"
    )