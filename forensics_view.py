from __future__ import annotations

import hashlib
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import numpy as np

_cv2: Any = cv2

try:
    import streamlit as st
except ImportError:
    st = None  # type: ignore[assignment]


class APEXForensicsEngine:
    """
    بزوێنەری فەحس و لێکۆڵینەوەی یاساییی تاوانباران (100% Offline Forensics Lab):
    1. دروستکردن و بەڕێوەبردنی دۆسیەی فەحس (Forensic Investigation Cases).
    2. کۆکردنەوەی زنجیرەی بەڵگەکان و کامێراکان لەسەر یەک تاوانبار یان گومانلێکراو.
    3. پشکنینی پەنجەمۆری SHA-256 و باشترکردنی ڕوونیی وێنەی بەڵگە (CLAHE Enhancement).
    """

    def __init__(self, db_name: str = "apex_security.db") -> None:
        self.project_root: Path = Path(__file__).resolve().parent
        self.db_path: Path = self.project_root / db_name
        self.snapshot_dir: Path = self.project_root / "apex_snapshots"
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        self.init_forensics_tables()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    def init_forensics_tables(self) -> None:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS forensic_cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_number TEXT UNIQUE NOT NULL,
                suspect_name TEXT NOT NULL,
                national_or_plate_id TEXT DEFAULT '',
                threat_level TEXT NOT NULL DEFAULT 'HIGH',
                case_status TEXT NOT NULL DEFAULT 'OPEN',
                evidence_hash TEXT DEFAULT '',
                investigator_notes TEXT DEFAULT '',
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    @staticmethod
    def compute_evidence_sha256(file_path: str) -> str:
        """هەژمارکردنی پەنجەمۆری یاساییی SHA-256 بۆ بەڵگە و وێنەکان."""
        if not file_path or not os.path.exists(file_path):
            return "NO_FILE_HASH"
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    @staticmethod
    def enhance_evidence_image(image_path: str) -> Optional[np.ndarray]:
        """باشترکردنی ڕوونیی وێنەی گومانلێکراو لە تاریکی یان دووریدا (100% Offline)."""
        if not image_path or not os.path.exists(image_path):
            return None
        img: Optional[np.ndarray] = _cv2.imread(image_path)
        if img is None or img.size == 0:
            return None

        lab: np.ndarray = _cv2.cvtColor(img, _cv2.COLOR_BGR2LAB)
        l_ch, a_ch, b_ch = _cv2.split(lab)
        clahe: Any = _cv2.createCLAHE(clipLimit=2.8, tileGridSize=(8, 8))
        l_enhanced: np.ndarray = clahe.apply(l_ch)
        merged: np.ndarray = _cv2.merge([l_enhanced, a_ch, b_ch])
        enhanced_bgr: np.ndarray = _cv2.cvtColor(merged, _cv2.COLOR_LAB2BGR)
        return enhanced_bgr

    def create_or_update_case(
        self,
        suspect_name: str,
        national_or_plate_id: str = "",
        threat_level: str = "HIGH",
        case_status: str = "OPEN",
        evidence_path: str = "",
        investigator_notes: str = "",
    ) -> str:
        """دروستکردنی دۆسیەی نوێی فەحس و بەستنەوەی بە بەڵگەوە."""
        now = datetime.now()
        now_str = now.strftime("%Y-%m-%d %H:%M:%S")
        case_num = f"CASE-{now.strftime('%Y%m%d-%H%M%S')}-{now.microsecond // 1000:03d}"
        ev_hash = self.compute_evidence_sha256(evidence_path)

        conn = self._connect()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO forensic_cases
            (case_number, suspect_name, national_or_plate_id, threat_level, case_status, evidence_hash, investigator_notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                case_num,
                str(suspect_name).strip(),
                str(national_or_plate_id).strip(),
                str(threat_level).upper(),
                str(case_status).upper(),
                ev_hash,
                str(investigator_notes).strip(),
                now_str,
            ),
        )
        conn.commit()
        conn.close()
        return case_num

    def update_case_status(self, case_id: int, new_status: str) -> bool:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute(
            "UPDATE forensic_cases SET case_status = ? WHERE id = ?",
            (str(new_status).upper(), int(case_id)),
        )
        ok = cur.rowcount > 0
        conn.commit()
        conn.close()
        return ok

    def list_cases(self, keyword: str = "") -> List[Dict[str, Any]]:
        conn = self._connect()
        cur = conn.cursor()
        if keyword.strip():
            lk = f"%{keyword.strip()}%"
            cur.execute(
                """
                SELECT id, case_number, suspect_name, national_or_plate_id, threat_level,
                       case_status, evidence_hash, investigator_notes, created_at
                FROM forensic_cases
                WHERE suspect_name LIKE ? OR case_number LIKE ? OR national_or_plate_id LIKE ?
                ORDER BY id DESC
                """,
                (lk, lk, lk),
            )
        else:
            cur.execute("""
                SELECT id, case_number, suspect_name, national_or_plate_id, threat_level,
                       case_status, evidence_hash, investigator_notes, created_at
                FROM forensic_cases
                ORDER BY id DESC
                """)
        rows = cur.fetchall()
        conn.close()

        cases: List[Dict[str, Any]] = []
        for r in rows:
            cases.append(
                {
                    "id": r[0],
                    "case_number": r[1],
                    "suspect_name": r[2],
                    "national_or_plate_id": r[3],
                    "threat_level": r[4],
                    "case_status": r[5],
                    "evidence_hash": r[6],
                    "investigator_notes": r[7],
                    "created_at": r[8],
                }
            )
        return cases


def render_forensics_view() -> None:
    """ڕووکاری بەشی فەحس و لێکۆڵینەوەی تاوانباران لە داشبۆردی APEX."""
    if st is None:
        return

    engine = APEXForensicsEngine()
    st.markdown("## 🔬 APEX FORENSICS & CRIMINAL INVESTIGATION LAB")

    snap_files = sorted(
        [
            str(p)
            for p in engine.snapshot_dir.glob("*.jpg")
            if p.is_file()
        ],
        reverse=True,
    )

    col_form, col_list = st.columns([1.25, 1.75])
    with col_form:
        with st.container(border=True):
            st.markdown("##### 📁 کردنەوەی دۆسیەی نوێی فەحس")
            s_name = str(st.text_input("ناوی تاوانبار / گومانلێکراو:", key="for_sus_name") or "")
            s_id = str(st.text_input("ژمارەی ناسنامە یان تابلۆ:", key="for_sus_id") or "")
            s_level = str(
                st.selectbox(
                    "ئاستی مەترسی:", ["CRITICAL", "HIGH", "MEDIUM", "LOW"], key="for_level"
                )
                or "HIGH"
            )
            ev_options = ["NONE"] + [os.path.basename(p) for p in snap_files[:30]]
            selected_ev_name = str(
                st.selectbox("بەستنەوەی بەڵگەی وێنەیی (SHA-256):", ev_options, key="for_ev_sel")
                or "NONE"
            )
            ev_path = (
                str(engine.snapshot_dir / selected_ev_name)
                if selected_ev_name != "NONE"
                else ""
            )
            s_notes = str(st.text_area("ڕاپۆرتی لێکۆڵەر:", key="for_notes") or "")
            if st.button("⚖️ تۆمارکردنی دۆسیەی فەحس", width="stretch", key="for_create_btn"):
                if s_name.strip():
                    c_num = engine.create_or_update_case(
                        suspect_name=s_name,
                        national_or_plate_id=s_id,
                        threat_level=s_level,
                        evidence_path=ev_path,
                        investigator_notes=s_notes,
                    )
                    st.success(f"دۆسیەی فەحس بە ژمارەی `{c_num}` دروست کرا.")

        if snap_files:
            with st.container(border=True):
                st.markdown("##### 🔍 تاقیگەی ڕووناککردنەوەی بەڵگە (CLAHE Enhancer)")
                lab_choice = str(
                    st.selectbox(
                        "وێنەی بەڵگە هەڵبژێرە:",
                        [os.path.basename(p) for p in snap_files[:20]],
                        key="for_lab_img",
                    )
                    or ""
                )
                if lab_choice:
                    full_lab_path = str(engine.snapshot_dir / lab_choice)
                    enhanced = engine.enhance_evidence_image(full_lab_path)
                    if enhanced is not None:
                        c_orig, c_enh = st.columns(2)
                        with c_orig:
                            st.caption("وێنەی ڕەسەن")
                            st.image(full_lab_path, width="stretch")
                        with c_enh:
                            st.caption("ڕووناککراوە (CLAHE)")
                            enh_rgb = _cv2.cvtColor(enhanced, _cv2.COLOR_BGR2RGB)
                            st.image(enh_rgb, width="stretch")
                        st.code(
                            f"SHA-256: {engine.compute_evidence_sha256(full_lab_path)}",
                            language="text",
                        )

    with col_list:
        search_q = str(st.text_input("گەڕان لە ناو دۆسیەکانی فەحس:", key="for_search_inp") or "")
        cases = engine.list_cases(search_q)
        if not cases:
            st.info("هیچ دۆسیەیەکی فەحس تۆمار نەکراوە.")
        else:
            for cs in cases:
                with st.expander(
                    f"⚖️ {cs['case_number']} | {cs['suspect_name']} [{cs['threat_level']}] — {cs['case_status']}"
                ):
                    st.write(
                        f"**ناسنامە/تابلۆ:** `{cs['national_or_plate_id']}` | **بەروار:** `{cs['created_at']}`"
                    )
                    st.write(
                        f"**پەنجەمۆری یاساییی بەڵگە (SHA-256):** `{cs['evidence_hash']}`"
                    )
                    st.write(f"**ڕاپۆرتی لێکۆڵەر:** {cs['investigator_notes']}")
                    new_st = str(
                        st.selectbox(
                            "گۆڕینی دۆخی دۆسیە:",
                            ["OPEN", "WANTED", "UNDER_REVIEW", "CLOSED"],
                            index=["OPEN", "WANTED", "UNDER_REVIEW", "CLOSED"].index(
                                cs["case_status"]
                            )
                            if cs["case_status"] in ["OPEN", "WANTED", "UNDER_REVIEW", "CLOSED"]
                            else 0,
                            key=f"st_sel_{cs['id']}",
                        )
                        or cs["case_status"]
                    )
                    if st.button("💾 نوێکردنەوەی دۆخ", key=f"st_btn_{cs['id']}"):
                        engine.update_case_status(int(cs["id"]), new_st)
                        st.success("دۆخی دۆسیەکە نوێ کرایەوە.")
                        st.rerun()


if __name__ == "__main__":
    f_engine = APEXForensicsEngine()
    new_case = f_engine.create_or_update_case(
        suspect_name="INVESTIGATION_TEST_SUBJECT",
        national_or_plate_id="22-A-9941",
        threat_level="CRITICAL",
        investigator_notes="Offline Forensics Verification",
    )
    all_cases = f_engine.list_cases("INVESTIGATION_TEST_SUBJECT")
    print(
        f"[FORENSICS VIEW] Offline Ready | Created Case: {new_case} | Total Matched: {len(all_cases)}"
    )