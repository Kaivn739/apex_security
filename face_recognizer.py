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
    بزوێنەری خێرا و مسۆگەری دۆزینەوە و ناسینەوەی ڕووخسار و تارگێتەکان (100% Offline):
    - دۆزینەوەی ڕووخسار بە هەرەمی خێرای 360px (5ms) بۆ گرتنی دەموچاوی نزیک و دوور بێ بارگرانی CPU.
    - ناسینەوەی تارگێتەکانی ناو فۆڵدەری targets/ و داتابەیسی ئەپێکس بە ڕەنگی سەوز.
    """

    def __init__(
        self,
        targets_dir: str = "targets",
        match_threshold: float = 0.36,
    ) -> None:
        self.targets_dir = (
            str(PROJECT_ROOT / targets_dir)
            if not os.path.isabs(targets_dir)
            else targets_dir
        )
        self.match_threshold = float(match_threshold)
        os.makedirs(self.targets_dir, exist_ok=True)

        self._cascades = self._load_face_cascades()
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
                    "haarcascade_frontalface_alt.xml",
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

    def _extract_core_face_features(self, face_bgr: np.ndarray) -> Optional[np.ndarray]:
        if face_bgr is None or face_bgr.size == 0:
            return None

        h, w = face_bgr.shape[:2]
        mx = int(w * 0.14)
        my = int(h * 0.12)
        core_roi = face_bgr[my : max(my + 1, h - my), mx : max(mx + 1, w - mx)]
        if core_roi.size == 0:
            core_roi = face_bgr

        resized = _cv2.resize(core_roi, (64, 64), interpolation=_cv2.INTER_AREA)
        gray = _cv2.cvtColor(resized, _cv2.COLOR_BGR2GRAY)

        clahe = _cv2.createCLAHE(clipLimit=2.5, tileGridSize=(4, 4))
        norm_gray = clahe.apply(gray)
        norm_gray = _cv2.GaussianBlur(norm_gray, (3, 3), 0)

        gx = _cv2.Sobel(norm_gray, _cv2.CV_32F, 1, 0, ksize=3)
        gy = _cv2.Sobel(norm_gray, _cv2.CV_32F, 0, 1, ksize=3)
        mag = _cv2.magnitude(gx, gy)
        mag_small = _cv2.resize(mag, (16, 16), interpolation=_cv2.INTER_AREA).flatten()
        _cv2.normalize(mag_small, mag_small)

        struct_small = _cv2.resize(
            norm_gray, (16, 16), interpolation=_cv2.INTER_AREA
        ).astype(np.float32)
        struct_vec = (
            (struct_small - float(np.mean(struct_small)))
            / (float(np.std(struct_small)) + 1e-5)
        ).flatten()
        _cv2.normalize(struct_vec, struct_vec)

        combined = np.concatenate([mag_small * 0.45, struct_vec * 0.55]).astype(
            np.float32
        )
        _cv2.normalize(combined, combined)
        return combined

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
                mx, my = int(w * 0.16), int(h * 0.12)
                crop = img[my : max(my + 1, h - my), mx : max(mx + 1, w - mx)]

            vec_normal = self._extract_core_face_features(crop)
            vec_mirror = self._extract_core_face_features(_cv2.flip(crop, 1))

            if vec_normal is not None:
                templates.append(
                    {
                        "name": display_name,
                        "file": fname,
                        "vec_normal": vec_normal,
                        "vec_mirror": (
                            vec_mirror if vec_mirror is not None else vec_normal
                        ),
                    }
                )

        self._gallery_templates = templates
        self._gallery_signature = sig

    def _match_against_targets(self, face_bgr: np.ndarray) -> Tuple[str, str, float]:
        self._refresh_target_gallery()
        if not self._gallery_templates:
            return "Unknown Subject", "UNKNOWN", 0.0

        probe_vec = self._extract_core_face_features(face_bgr)
        if probe_vec is None:
            return "Unknown Subject", "UNKNOWN", 0.0

        best_name = "Unknown Subject"
        best_sim = 0.0

        for tpl in self._gallery_templates:
            sim_n = float(np.dot(probe_vec, tpl["vec_normal"]))
            sim_m = float(np.dot(probe_vec, tpl["vec_mirror"]))
            sim = max(sim_n, sim_m, 0.0)
            if sim > best_sim:
                best_sim = sim
                best_name = tpl["name"]

        confidence_pct = round(min(99.5, max(0.0, best_sim * 100.0)), 1)
        if best_sim >= self.match_threshold:
            return best_name, "MATCHED", confidence_pct
        return "Unknown Subject", "UNKNOWN", confidence_pct

    def _detect_face_regions(
        self, frame: np.ndarray
    ) -> List[Tuple[int, int, int, int]]:
        h, w = frame.shape[:2]
        if h < 36 or w < 36 or not self._cascades:
            return []

        # بچووککردنەوە بۆ 360px تا دۆزینەوەی ڕووخسار لە 5 میلی-چرکەدا تەواو ببێت
        target_w = 360
        if w > target_w:
            scale = target_w / float(w)
            small_h = max(36, int(h * scale))
            small_bgr = _cv2.resize(
                frame, (target_w, small_h), interpolation=_cv2.INTER_LINEAR
            )
            inv_scale = float(w) / float(target_w)
        else:
            small_bgr = frame
            inv_scale = 1.0

        gray_raw = _cv2.cvtColor(small_bgr, _cv2.COLOR_BGR2GRAY)
        clahe = _cv2.createCLAHE(clipLimit=2.2, tileGridSize=(6, 6))
        gray_clahe = clahe.apply(gray_raw)

        for test_gray in (gray_clahe, gray_raw):
            for clf in self._cascades:
                rects = clf.detectMultiScale(
                    test_gray,
                    scaleFactor=1.1,
                    minNeighbors=3,
                    minSize=(28, 28),
                )
                if len(rects) > 0:
                    mapped: List[Tuple[int, int, int, int]] = []
                    for x, y, bw, bh in rects:
                        rx = int(x * inv_scale)
                        ry = int(y * inv_scale)
                        rw = int(bw * inv_scale)
                        rh = int(bh * inv_scale)
                        mapped.append((rx, ry, rw, rh))
                    mapped.sort(key=lambda r: r[2] * r[3], reverse=True)
                    return mapped[:5]

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
                box_color = (0, 255, 0)
                label_txt = f"TARGET: {target_name} ({score}%)"
            else:
                box_color = (0, 165, 255)
                label_txt = f"FACE: {target_name} ({score}%)"

            _cv2.rectangle(frame, (x, y), (x + w, y + h), box_color, 3)
            banner_w = max(w, len(label_txt) * 10 + 16)
            _cv2.rectangle(
                frame, (x, max(0, y - 26)), (x + banner_w, y), (15, 23, 42), -1
            )
            _cv2.putText(
                frame,
                label_txt,
                (x + 6, max(17, y - 7)),
                _cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                box_color,
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


if __name__ == "__main__":
    engine = FaceRecognizerEngine()
    sample = np.zeros((360, 640, 3), dtype=np.uint8)
    _, items = engine.process_frame_with_details(sample)
    print(
        f"[FACE RECOGNIZER] Ultra-Fast Pyramid Ready | Targets Loaded: {len(engine._gallery_templates)} | Detections: {len(items)}"
    )
