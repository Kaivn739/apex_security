from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

_cv2: Any = cv2
PROJECT_ROOT = Path(__file__).resolve().parent
DB_PATH = PROJECT_ROOT / "apex_security.db"


class FaceRecognizerEngine:
    """
    بزوێنەری خێرا و وردی دۆزینەوە و ناسینەوەی تارگێتەکان (100% Offline):
    - دۆزینەوەی ڕووخسار بە فرە-پێوەر (CLAHE + Normal Gray + Equalized Gray) بۆ گرتنی ڕووخسار لە گۆشە و ڕووناکیی جیاوازدا.
    - بەراوردکردنی ناوەندی ڕووخسار لەگەڵ هەموو وێنەکانی ناو targets/ و داتابەیس.
    """

    def __init__(
        self,
        targets_dir: str = "targets",
        match_threshold: float = 0.24,
    ) -> None:
        self.targets_dir = (
            str(PROJECT_ROOT / targets_dir)
            if not os.path.isabs(targets_dir)
            else targets_dir
        )
        self.match_threshold = float(match_threshold)
        os.makedirs(self.targets_dir, exist_ok=True)

        self._cascades = self._load_face_cascades()
        self._clahe = _cv2.createCLAHE(clipLimit=2.4, tileGridSize=(8, 8))
        self._gallery_signature: Tuple[Tuple[str, float], ...] = ()
        self._gallery_templates: List[Dict[str, Any]] = []
        self._refresh_target_gallery()

    def _load_face_cascades(self) -> List[Any]:
        loaded: List[Any] = []
        try:
            data_dir = getattr(getattr(_cv2, "data", None), "haarcascades", "")
            if data_dir:
                for xml_name in (
                    "haarcascade_frontalface_default.xml",
                    "haarcascade_frontalface_alt2.xml",
                    "haarcascade_profileface.xml",
                ):
                    xml_path = os.path.join(data_dir, xml_name)
                    if os.path.exists(xml_path):
                        clf = _cv2.CascadeClassifier(xml_path)
                        if not clf.empty():
                            loaded.append(clf)
        except Exception:
            pass
        return loaded

    def _lookup_db_target_name(self, file_path: str, fallback_name: str) -> str:
        try:
            if DB_PATH.exists():
                conn = sqlite3.connect(str(DB_PATH), timeout=5.0)
                cur = conn.cursor()
                cur.execute(
                    "SELECT name FROM targets WHERE image_path LIKE ? ORDER BY id DESC LIMIT 1",
                    (f"%{os.path.basename(file_path)}",),
                )
                row = cur.fetchone()
                conn.close()
                if row and str(row[0]).strip():
                    return str(row[0]).strip()
        except Exception:
            pass
        return fallback_name

    def _compute_face_signature(
        self, face_bgr: np.ndarray
    ) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        if face_bgr is None or face_bgr.size == 0:
            return None

        h, w = face_bgr.shape[:2]
        mx, my = int(w * 0.12), int(h * 0.10)
        roi = face_bgr[my : max(my + 1, h - my), mx : max(mx + 1, w - mx)]
        if roi.size == 0:
            roi = face_bgr

        gray = _cv2.cvtColor(roi, _cv2.COLOR_BGR2GRAY)
        gray_eq = self._clahe.apply(_cv2.resize(gray, (48, 48)))

        vec = gray_eq.astype(np.float32).flatten()
        vec = (vec - float(np.mean(vec))) / (float(np.std(vec)) + 1e-5)
        _cv2.normalize(vec, vec)

        hist = _cv2.calcHist([gray_eq], [0], None, [32], [0, 256]).flatten()
        _cv2.normalize(hist, hist)
        return vec, hist

    def _refresh_target_gallery(self) -> None:
        if not os.path.exists(self.targets_dir):
            self._gallery_templates = []
            self._gallery_signature = ()
            return

        files_meta: List[Tuple[str, float]] = []
        for fname in sorted(os.listdir(self.targets_dir)):
            if fname.lower().endswith((".jpg", ".jpeg", ".png", ".bmp")):
                fpath = os.path.join(self.targets_dir, fname)
                try:
                    files_meta.append((fname, os.path.getmtime(fpath)))
                except OSError:
                    continue

        sig = tuple(files_meta)
        if sig == self._gallery_signature:
            return

        templates: List[Dict[str, Any]] = []
        for fname, _ in files_meta:
            fpath = os.path.join(self.targets_dir, fname)
            img = _cv2.imread(fpath)
            if img is None or img.size == 0:
                continue

            fallback_name = os.path.splitext(fname)[0].replace("_", " ").strip().title()
            display_name = self._lookup_db_target_name(fpath, fallback_name)

            faces = self._detect_face_regions(img)
            if faces:
                fx, fy, fw, fh = max(faces, key=lambda b: b[2] * b[3])
                crop = img[fy : fy + fh, fx : fx + fw]
            else:
                h, w = img.shape[:2]
                mx, my = int(w * 0.14), int(h * 0.12)
                crop = img[my : max(my + 1, h - my), mx : max(mx + 1, w - mx)]

            sig_n = self._compute_face_signature(crop)
            sig_m = self._compute_face_signature(_cv2.flip(crop, 1))
            if sig_n is not None:
                templates.append(
                    {
                        "name": display_name,
                        "vec_n": sig_n[0],
                        "hist_n": sig_n[1],
                        "vec_m": sig_m[0] if sig_m is not None else sig_n[0],
                        "hist_m": sig_m[1] if sig_m is not None else sig_n[1],
                    }
                )

        self._gallery_templates = templates
        self._gallery_signature = sig

    def _match_against_targets(self, face_bgr: np.ndarray) -> Tuple[str, str, float]:
        self._refresh_target_gallery()
        if not self._gallery_templates:
            return "Unknown Subject", "UNKNOWN", 0.0

        probe = self._compute_face_signature(face_bgr)
        if probe is None:
            return "Unknown Subject", "UNKNOWN", 0.0

        p_vec, p_hist = probe
        best_name = "Unknown Subject"
        best_score = 0.0

        for tpl in self._gallery_templates:
            dot_n = max(0.0, float(np.dot(p_vec, tpl["vec_n"])))
            dot_m = max(0.0, float(np.dot(p_vec, tpl["vec_m"])))
            struct_sim = max(dot_n, dot_m)

            hist_n = max(
                0.0, float(_cv2.compareHist(p_hist, tpl["hist_n"], _cv2.HISTCMP_CORREL))
            )
            hist_m = max(
                0.0, float(_cv2.compareHist(p_hist, tpl["hist_m"], _cv2.HISTCMP_CORREL))
            )
            hist_sim = max(hist_n, hist_m)

            combined = (struct_sim * 0.65) + (hist_sim * 0.35)
            if combined > best_score:
                best_score = combined
                best_name = tpl["name"]

        pct = round(min(99.5, max(0.0, best_score * 100.0)), 1)
        if best_score >= self.match_threshold:
            return best_name, "MATCHED", pct
        return "Unknown Subject", "UNKNOWN", pct

    def _detect_face_regions(
        self, frame: np.ndarray
    ) -> List[Tuple[int, int, int, int]]:
        if frame is None or frame.size == 0 or not self._cascades:
            return []

        h_orig, w_orig = frame.shape[:2]
        target_w = 480.0
        scale = target_w / float(max(w_orig, 1)) if w_orig > 500 else 1.0
        small = (
            _cv2.resize(frame, (int(w_orig * scale), int(h_orig * scale)))
            if scale < 1.0
            else frame
        )
        inv = 1.0 / scale

        gray = _cv2.cvtColor(small, _cv2.COLOR_BGR2GRAY)
        gray_eq = self._clahe.apply(gray)
        gray_hist = _cv2.equalizeHist(gray)

        for img_pass in (gray_eq, gray, gray_hist):
            for clf in self._cascades:
                rects = clf.detectMultiScale(
                    img_pass,
                    scaleFactor=1.06,
                    minNeighbors=2,
                    minSize=(22, 22),
                )
                if len(rects) > 0:
                    boxes: List[Tuple[int, int, int, int]] = []
                    for x, y, w, h in rects[:4]:
                        boxes.append(
                            (
                                max(0, int(x * inv)),
                                max(0, int(y * inv)),
                                min(w_orig, int(w * inv)),
                                min(h_orig, int(h * inv)),
                            )
                        )
                    return boxes
        return []

    def process_frame_with_details(
        self, frame: np.ndarray
    ) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
        if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
            return frame, []

        detected_targets: List[Dict[str, Any]] = []
        faces = self._detect_face_regions(frame)

        for x, y, w, h in faces:
            face_crop = frame[y : y + h, x : x + w]
            target_name, status, score = self._match_against_targets(face_crop)

            if status == "MATCHED":
                color = (0, 255, 0)
                label = f"TARGET: {target_name} ({score}%)"
            else:
                color = (0, 165, 255)
                label = f"FACE: {target_name} ({score}%)"

            _cv2.rectangle(frame, (x, y), (x + w, y + h), color, 3)
            _cv2.rectangle(
                frame,
                (x, max(0, y - 26)),
                (x + max(w, len(label) * 9 + 14), y),
                (15, 23, 42),
                -1,
            )
            _cv2.putText(
                frame,
                label,
                (x + 5, max(18, y - 7)),
                _cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                color,
                2,
            )

            detected_targets.append(
                {
                    "name": target_name,
                    "status": status,
                    "score": score,
                    "bbox": (x, y, w, h),
                    "time": time.strftime("%H:%M:%S"),
                }
            )

        return frame, detected_targets

    def register_target_image(self, name: str, image_bgr: np.ndarray) -> str:
        safe_name = "".join(
            c if c.isalnum() or c in (" ", "-", "_") else "_" for c in name
        ).strip()
        safe_name = safe_name.replace(" ", "_").lower() or f"target_{int(time.time())}"
        out_path = os.path.join(self.targets_dir, f"{safe_name}.jpg")
        _cv2.imwrite(out_path, image_bgr)
        self._refresh_target_gallery()
        return out_path

    def process_frame(self, frame: np.ndarray) -> np.ndarray:
        processed, _ = self.process_frame_with_details(frame)
        return processed

    def detect_and_draw(
        self, frame: np.ndarray, enabled: bool = True
    ) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
        if not enabled:
            return frame, []
        return self.process_frame_with_details(frame)


APEXFaceRecognizer = FaceRecognizerEngine
FaceRecognizer = FaceRecognizerEngine
