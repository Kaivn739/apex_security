from __future__ import annotations

import os
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

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

try:
    from cyber_shield import APEXCyberShield
except ImportError:
    APEXCyberShield = None  # type: ignore[assignment,misc]


class APEXDatabaseLifecycleManager:
    """
    بەڕێوەبەری داتابەیسی ٤-قۆناغی و کارتی ئەرشیفی خۆکار (100% Offline SQLite WAL):
    1. ڕاستەوخۆ / ڕۆژانە (Live / 24 Hours)
    2. مانگانە (Monthly: 1 - 30 Days)
    3. ساڵانە (Yearly: 31 - 365 Days)
    4. ئەرشیفی گشتی (Historical Archive: > 365 Days + گەڕان بە ساڵ و تارگێت)
    """

    def __init__(self, db_name: str = "apex_security.db") -> None:
        self.project_root: Path = Path(__file__).resolve().parent
        self.db_path: Path = self.project_root / db_name
        self.snapshot_dir: Path = self.project_root / "apex_snapshots"
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        self._shield: Any = (
            APEXCyberShield(self.project_root, db_name)
            if APEXCyberShield is not None
            else None
        )
        self._recent_event_guard: Dict[str, float] = {}
        self.init_tables()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def init_tables(self) -> None:
        """دروستکردنی خشتەکانی داتابەیس و پشکنینی ستوونە پێویستەکان."""
        conn = self._connect()
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS apex_archive_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_code TEXT NOT NULL,
                target_name TEXT NOT NULL,
                event_type TEXT NOT NULL,
                camera_id TEXT NOT NULL,
                location_name TEXT NOT NULL,
                severity TEXT NOT NULL DEFAULT 'MEDIUM',
                snapshot_path TEXT DEFAULT '',
                notes TEXT DEFAULT '',
                archive_stage TEXT NOT NULL DEFAULT 'DAILY_24H',
                created_at TEXT NOT NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS targets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                target_type TEXT NOT NULL,
                status TEXT NOT NULL,
                plate_or_id TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        conn.commit()
        conn.close()

    def _clean_text(self, value: str, max_len: int = 120) -> str:
        if self._shield is not None:
            return str(self._shield.sanitize_text_input(value, max_length=max_len))
        return str(value).strip()[:max_len]

    def save_street_snapshot(
        self, frame: Optional[np.ndarray], camera_id: str, tag: str
    ) -> str:
        """گرتن و پاشەکەوتکردنی وێنەی سەر شەقام بۆ کارتی ئەرشیفی خۆکار."""
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        safe_cam = self._clean_text(camera_id, 24).replace(" ", "_")
        safe_tag = self._clean_text(tag, 24).replace(" ", "_")
        file_path = self.snapshot_dir / f"{safe_cam}_{safe_tag}_{stamp}.jpg"

        if frame is not None and isinstance(frame, np.ndarray) and frame.size > 0:
            _cv2.imwrite(str(file_path), frame)
        else:
            placeholder = np.zeros((240, 420, 3), dtype=np.uint8)
            placeholder[:] = (22, 28, 38)
            _cv2.rectangle(placeholder, (8, 8), (412, 232), (0, 200, 150), 2)
            _cv2.putText(
                placeholder,
                f"APEX CAPTURE | {safe_cam}",
                (20, 95),
                _cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (0, 230, 180),
                2,
            )
            _cv2.putText(
                placeholder,
                f"EVENT: {safe_tag}",
                (20, 140),
                _cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (255, 255, 255),
                1,
            )
            _cv2.imwrite(str(file_path), placeholder)

        return str(file_path)

    def log_detection_record(
        self,
        target_name: str,
        event_type: str,
        camera_id: str = "CAM-01",
        location_name: str = "Main Sector Gate",
        severity: str = "HIGH",
        frame: Optional[np.ndarray] = None,
        notes: str = "",
        created_at: Optional[str] = None,
    ) -> int:
        """تۆمارکردنی ڕووداوی نوێ و دروستکردنی کارتی ئەرشیفی خۆکار."""
        clean_target = self._clean_text(target_name, 80) or "UNKNOWN_TARGET"
        clean_type = self._clean_text(event_type, 40) or "ALERT"
        clean_cam = self._clean_text(camera_id, 30) or "CAM-01"
        clean_loc = self._clean_text(location_name, 80) or "Sector 1"
        clean_sev = self._clean_text(severity, 20).upper() or "MEDIUM"
        clean_notes = self._clean_text(notes, 200)

        snap_path = self.save_street_snapshot(frame, clean_cam, clean_type)
        ts = created_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        case_code = f"APX-{datetime.now().strftime('%y%m%d')}-{os.getpid() % 1000:03d}"

        conn = self._connect()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO apex_archive_records
            (case_code, target_name, event_type, camera_id, location_name, severity, snapshot_path, notes, archive_stage, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'DAILY_24H', ?)
            """,
            (
                case_code,
                clean_target,
                clean_type,
                clean_cam,
                clean_loc,
                clean_sev,
                snap_path,
                clean_notes,
                ts,
            ),
        )
        record_id = int(cur.lastrowid or 0)
        conn.commit()
        conn.close()
        return record_id

    def run_lifecycle_rotation(self) -> Dict[str, int]:
        """
        گواستنەوەی خۆکاری تۆمارەکان بەپێی تەمەنیان:
        - کەمتر لە ٢٤ سەعات -> DAILY_24H
        - ١ تا ٣٠ ڕۆژ -> MONTHLY
        - ٣١ تا ٣٦٥ ڕۆژ -> YEARLY
        - زیاتر لە ٣٦٥ ڕۆژ -> HISTORICAL_ARCHIVE
        """
        now = datetime.now()
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("SELECT id, created_at, archive_stage FROM apex_archive_records")
        rows = cur.fetchall()

        updated_counts = {
            "DAILY_24H": 0,
            "MONTHLY": 0,
            "YEARLY": 0,
            "HISTORICAL_ARCHIVE": 0,
        }
        for rec_id, created_str, old_stage in rows:
            try:
                dt = datetime.strptime(str(created_str), "%Y-%m-%d %H:%M:%S")
            except ValueError:
                dt = now

            age = now - dt
            if age <= timedelta(hours=24):
                new_stage = "DAILY_24H"
            elif age <= timedelta(days=30):
                new_stage = "MONTHLY"
            elif age <= timedelta(days=365):
                new_stage = "YEARLY"
            else:
                new_stage = "HISTORICAL_ARCHIVE"

            updated_counts[new_stage] += 1
            if new_stage != old_stage:
                cur.execute(
                    "UPDATE apex_archive_records SET archive_stage = ? WHERE id = ?",
                    (new_stage, int(rec_id)),
                )

        conn.commit()
        conn.close()
        return updated_counts

    def fetch_records(
        self,
        stage: Optional[str] = None,
        search_query: str = "",
        year_filter: str = "ALL",
        limit: int = 100,
        run_rotation: bool = True,
    ) -> List[Dict[str, Any]]:
        """هێنانی داتاکان بەپێی قۆناغ، ناوی تارگێت، ژمارەی فەحس، یان ساڵ."""
        if run_rotation:
            self.run_lifecycle_rotation()
        conn = self._connect()
        cur = conn.cursor()

        query = """
            SELECT id, case_code, target_name, event_type, camera_id, location_name,
                   severity, snapshot_path, notes, archive_stage, created_at
            FROM apex_archive_records
            WHERE 1=1
        """
        params: List[Any] = []

        if stage and stage != "ALL":
            query += " AND archive_stage = ?"
            params.append(stage)

        if year_filter and year_filter != "ALL":
            query += " AND substr(created_at, 1, 4) = ?"
            params.append(str(year_filter))

        if search_query.strip():
            like_val = f"%{self._clean_text(search_query, 60)}%"
            query += " AND (target_name LIKE ? OR case_code LIKE ? OR location_name LIKE ? OR event_type LIKE ?)"
            params.extend([like_val, like_val, like_val, like_val])

        query += " ORDER BY id DESC LIMIT ?"
        params.append(int(limit))

        cur.execute(query, params)
        rows = cur.fetchall()
        conn.close()

        results: List[Dict[str, Any]] = []
        for r in rows:
            results.append(
                {
                    "id": r[0],
                    "case_code": r[1],
                    "target_name": r[2],
                    "event_type": r[3],
                    "camera_id": r[4],
                    "location_name": r[5],
                    "severity": r[6],
                    "snapshot_path": r[7],
                    "notes": r[8],
                    "archive_stage": r[9],
                    "created_at": r[10],
                }
            )
        return results

    def update_record(
        self, record_id: int, target_name: str, location_name: str, notes: str
    ) -> bool:
        """چاککردن و نوێکردنەوەی زانیاریی تۆمارێک لەلایەن بەکارهێنەرەوە."""
        conn = self._connect()
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE apex_archive_records
            SET target_name = ?, location_name = ?, notes = ?
            WHERE id = ?
            """,
            (
                self._clean_text(target_name, 80),
                self._clean_text(location_name, 80),
                self._clean_text(notes, 200),
                int(record_id),
            ),
        )
        ok = cur.rowcount > 0
        conn.commit()
        conn.close()
        return ok

    def attach_to_internal_cpu(self) -> None:
        """بەستنەوەی خۆکار بە CPU ناوخۆیی لەگەڵ پارێزگاری دژی دووبارەبوونەوەی خێرا."""
        if get_internal_cpu is None:
            return

        def _on_event(ev: Any) -> None:
            cam_id = str(getattr(ev, "camera_id", "CAM-01"))
            ev_type = str(getattr(ev, "event_type", "AI_EVENT"))
            title = str(getattr(ev, "title", "ALERT"))
            guard_key = f"{cam_id}:{ev_type}:{title}"
            now = time.monotonic()
            last_ts = self._recent_event_guard.get(guard_key, 0.0)
            if (now - last_ts) < 8.0:
                return
            self._recent_event_guard[guard_key] = now

            self.log_detection_record(
                target_name=title,
                event_type=ev_type,
                camera_id=cam_id,
                location_name=f"Zone-{cam_id}",
                severity=str(getattr(ev, "severity", "HIGH")),
                notes=str(getattr(ev, "details", "")),
            )

        get_internal_cpu().register_event_listener(_on_event)


def render_db_manager_view() -> None:
    """ڕووکاری تابی داتابەیس لە داشبۆردی APEX (٤ قۆناغ + کارتی ئەرشیفی خۆکار)."""
    if st is None:
        return

    manager = APEXDatabaseLifecycleManager()
    counts = manager.run_lifecycle_rotation()

    st.markdown("## 🗄️ APEX DATABASE & 4-STAGE ARCHIVE")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("⏱️ ڕاستەوخۆ (٢٤ سەعات)", counts["DAILY_24H"])
    c2.metric("📅 مانگانە (٣٠ ڕۆژ)", counts["MONTHLY"])
    c3.metric("📆 ساڵانە (٣٦٥ ڕۆژ)", counts["YEARLY"])
    c4.metric("🏛️ ئەرشیفی ساڵانی ڕابردوو", counts["HISTORICAL_ARCHIVE"])

    st.markdown("---")
    f_col1, f_col2, f_col3 = st.columns([1.4, 1.8, 1.0])
    with f_col1:
        stage_label = str(
            st.selectbox(
                "قۆناغی ئەرشیف:",
                ["ALL", "DAILY_24H", "MONTHLY", "YEARLY", "HISTORICAL_ARCHIVE"],
                key="apex_db_stage_sel",
            )
            or "ALL"
        )
    with f_col2:
        search_txt = str(
            st.text_input(
                "گەڕانی خێرا (ناوی تارگێت یان ژمارەی فەحس):",
                placeholder="نموونە: APX-261116 یان ناوی تارگێت...",
                key="apex_db_search_inp",
            )
            or ""
        )
    with f_col3:
        year_sel = str(
            st.selectbox(
                "سلایدی ساڵانی ڕابردوو:",
                ["ALL", "2026", "2025", "2024", "2023"],
                key="apex_db_year_sel",
            )
            or "ALL"
        )

    records = manager.fetch_records(
        stage=stage_label,
        search_query=search_txt,
        year_filter=year_sel,
        run_rotation=False,
    )

    left_col, right_col = st.columns([2.2, 1.2])
    with left_col:
        st.markdown("##### 📋 تۆمارەکانی داتابەیس و ئەرشیف")
        if not records:
            st.info("هیچ تۆمارێک لەم قۆناغەدا نەدۆزرایەوە.")
        else:
            for rec in records[:25]:
                with st.expander(
                    f"[{rec['case_code']}] {rec['target_name']} — {rec['event_type']} ({rec['created_at']})"
                ):
                    st.write(
                        f"**کامێرا:** {rec['camera_id']} | **شوێن:** {rec['location_name']} | **ئاست:** {rec['severity']}"
                    )
                    new_t = str(
                        st.text_input(
                            "ناوی تارگێت:",
                            value=str(rec["target_name"]),
                            key=f"edt_t_{rec['id']}",
                        )
                        or ""
                    )
                    new_l = str(
                        st.text_input(
                            "شوێن:",
                            value=str(rec["location_name"]),
                            key=f"edt_l_{rec['id']}",
                        )
                        or ""
                    )
                    new_n = str(
                        st.text_input(
                            "تێبینی:", value=str(rec["notes"]), key=f"edt_n_{rec['id']}"
                        )
                        or ""
                    )
                    if st.button(
                        "💾 پاشەکەوتکردنی گۆڕانکاری", key=f"save_rec_{rec['id']}"
                    ):
                        manager.update_record(int(rec["id"]), new_t, new_l, new_n)
                        st.success("تۆمارەکە بە سەرکەوتوویی نوێ کرایەوە.")

        with st.expander("➕ زیادکردنی زانیاریی نوێ بۆ داتابەیس"):
            add_target = str(
                st.text_input("ناوی تارگێت / کەس / تابلۆ:", key="apex_db_add_target")
                or ""
            )
            add_type = str(
                st.selectbox(
                    "جۆری ڕووداو:",
                    [
                        "TARGET_MATCH",
                        "ALPR_PLATE",
                        "WEAPON",
                        "FIRE_SMOKE",
                        "CROWD_DISTRESS",
                    ],
                    key="apex_db_add_type",
                )
                or "TARGET_MATCH"
            )
            add_cam = str(
                st.text_input("کامێرا:", value="CAM-01", key="apex_db_add_cam")
                or "CAM-01"
            )
            add_loc = str(
                st.text_input("شوێن:", value="Main Gate", key="apex_db_add_loc")
                or "Main Gate"
            )
            add_notes = str(
                st.text_input("تێبینی و وردەکاری:", key="apex_db_add_notes") or ""
            )
            if st.button("📥 تۆمارکردن لە داتابەیس", key="apex_db_add_btn"):
                if add_target.strip():
                    new_id = manager.log_detection_record(
                        target_name=add_target,
                        event_type=add_type,
                        camera_id=add_cam,
                        location_name=add_loc,
                        notes=add_notes,
                    )
                    st.success(f"تۆماری نوێ بە ژمارەی #{new_id} زیاد کرا.")

    with right_col:
        st.markdown("##### 📸 کارتی ئەرشیفکردنی خۆکار (Auto-Snapshot Card)")
        if records:
            latest = records[0]
            with st.container(border=True):
                snap_file = str(latest.get("snapshot_path", ""))
                if snap_file and os.path.exists(snap_file):
                    st.image(snap_file, width="stretch")
                st.markdown(f"**🎯 تارگێت:** `{latest['target_name']}`")
                st.markdown(
                    f"**📍 شوێن:** {latest['location_name']} ({latest['camera_id']})"
                )
                st.markdown(f"**🕒 کاتی دۆزینەوە:** `{latest['created_at']}`")
                st.markdown(f"**🗂️ قۆناغ:** `{latest['archive_stage']}`")
        else:
            st.info("لەگەڵ یەکەم ئاگاداریدا کارتی وێنەی سەر شەقام لێرە دەردەکەوێت.")


if __name__ == "__main__":
    db_mgr = APEXDatabaseLifecycleManager()
    rec_id = db_mgr.log_detection_record(
        target_name="TEST_TARGET_01",
        event_type="FACE_MATCH",
        camera_id="CAM-01",
        location_name="North Gate Sector",
        severity="HIGH",
        notes="Offline Lifecycle Test",
    )
    summary = db_mgr.run_lifecycle_rotation()
    rows = db_mgr.fetch_records(stage="DAILY_24H", search_query="TEST_TARGET_01")
    print(
        f"[DB MANAGER VIEW] Offline Ready | Inserted ID: {rec_id} | Stages: {summary} | Fetched: {len(rows)}"
    )