from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

_cv2: Any = cv2


class FaceRecognizerEngine:
    """
    بزوێنەری ڕاستەقینەی دۆزینەوە و ناسینەوەی ڕووخسار و تارگێتەکان (100% Offline):
    - دۆزینەوەی وردی ڕووخسار بە Haar Cascade + پشتڕاستکردنەوەی پێکهاتەی ڕووخسار.
    - دەرهێنانی پەنجەمۆری بینایی (CLAHE Histogram + ORB Keypoints) بۆ وێنەکانی ناو فۆڵدەری targets/.
    - بەراوردکردنی ڕاستەقینە و پێدانی ڕێژەی دڵنیایی راستەقینە (نەک ژمارەی جێگیر).
    """

    def __init__(
        self,
        targets_dir: str = "targets",
        match_threshold: float = 0.68,
    ) -> None:
        self.targets_dir = targets_dir
        self.match_threshold = float(match_threshold)
        if not os.path.exists(self.targets_dir):
            os.makedirs(self.targets_dir, exist_ok=True)

        self._face_cascade = self._load_frontal_cascade()
        self._orb = _cv2.ORB_create(nfeatures=256)
        self._bf = _cv2.BFMatcher(_cv2.NORM_HAMMING, crossCheck=True)

        self._gallery_signature: Tuple[Tuple[str, float], ...] = ()
        self._gallery_templates: List[Dict[str, Any]] = []
        self._refresh_target_gallery()

    def _load_frontal_cascade(self) -> Any:
        try:
            data_dir = getattr(getattr(_cv2, "data", None), "haarcascades", "")
            if data_dir:
                xml_path = os.path.join(data_dir, "haarcascade_frontalface_default.xml")
                if os.path.exists(xml_path):
                    clf = _cv2.CascadeClassifier(xml_path)
                    if not clf.empty():
                        return clf
        except Exception:
            pass
        return None

    def _extract_face_signature(
        self, face_bgr: np.ndarray
    ) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """دروستکردنی پەنجەمۆری بینایی (Normalized Grid Histogram + ORB Descriptors) بۆ ڕووخسار."""
        if face_bgr is None or face_bgr.size == 0:
            return None, None

        resized = _cv2.resize(face_bgr, (128, 128), interpolation=_cv2.INTER_AREA)
        gray = _cv2.cvtColor(resized, _cv2.COLOR_BGR2GRAY)
        clahe = _cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        norm_gray = clahe.apply(gray)

        # دابەشکردنی ڕووخسار بۆ ٤x٤ خانە (چاو، برۆ، لووت، دەم) بۆ وردیی بەرز
        hist_parts: List[np.ndarray] = []
        cell_h, cell_w = 32, 32
        for r in range(4):
            for c in range(4):
                patch = norm_gray[
                    r * cell_h : (r + 1) * cell_h, c * cell_w : (c + 1) * cell_w
                ]
                h = _cv2.calcHist([patch], [0], None, [32], [0, 256])
                _cv2.normalize(h, h)
                hist_parts.append(h.flatten())

        descriptor_vec = np.concatenate(hist_parts).astype(np.float32)
        _cv2.normalize(descriptor_vec, descriptor_vec)

        _, orb_desc = self._orb.detectAndCompute(norm_gray, None)
        return descriptor_vec, orb_desc

    def _refresh_target_gallery(self) -> None:
        """نوێکردنەوەی خۆکارانەی گەلەری تارگێتەکان تەنها کاتێک فایلی ناو targets/ بگۆڕێت."""
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

            clean_name = os.path.splitext(fname)[0].replace("_", " ").strip().title()
            faces = self._detect_face_regions(img)
            if faces:
                fx, fy, fw, fh = max(faces, key=lambda b: b[2] * b[3])
                crop = img[fy : fy + fh, fx : fx + fw]
            else:
                h, w = img.shape[:2]
                margin_x, margin_y = int(w * 0.12), int(h * 0.12)
                crop = img[
                    margin_y : max(margin_y + 1, h - margin_y),
                    margin_x : max(margin_x + 1, w - margin_x),
                ]

            vec, orb_desc = self._extract_face_signature(crop)
            if vec is not None:
                templates.append(
                    {
                        "name": clean_name,
                        "file": fname,
                        "vec": vec,
                        "orb": orb_desc,
                    }
                )

        self._gallery_templates = templates
        self._gallery_signature = sig

    def _match_against_targets(self, face_bgr: np.ndarray) -> Tuple[str, str, float]:
        """بەراوردکردنی ڕووخساری دۆزراوە لەگەڵ هەموو تارگێتە تۆمارکراوەکان."""
        self._refresh_target_gallery()
        if not self._gallery_templates:
            return "Unknown Subject", "UNKNOWN", 0.0

        probe_vec, probe_orb = self._extract_face_signature(face_bgr)
        if probe_vec is None:
            return "Unknown Subject", "UNKNOWN", 0.0

        best_name = "Unknown Subject"
        best_sim = 0.0

        for tpl in self._gallery_templates:
            hist_sim = float(
                _cv2.compareHist(probe_vec, tpl["vec"], _cv2.HISTCMP_CORREL)
            )
            hist_sim = max(0.0, min(1.0, hist_sim))

            orb_sim = 0.0
            if (
                probe_orb is not None
                and tpl["orb"] is not None
                and len(probe_orb) >= 8
                and len(tpl["orb"]) >= 8
            ):
                try:
                    matches = self._bf.match(probe_orb, tpl["orb"])
                    good = [m for m in matches if m.distance < 52]
                    denom = float(min(len(probe_orb), len(tpl["orb"])))
                    orb_sim = min(1.0, len(good) / max(1.0, denom * 0.45))
                except Exception:
                    orb_sim = 0.0

            combined = (hist_sim * 0.72) + (orb_sim * 0.28) if orb_sim > 0 else hist_sim
            if combined > best_sim:
                best_sim = combined
                best_name = tpl["name"]

        confidence_pct = round(best_sim * 100.0, 1)
        if best_sim >= self.match_threshold:
            return best_name, "MATCHED", confidence_pct
        return "Unknown Subject", "UNKNOWN", confidence_pct

    def _detect_face_regions(
        self, frame: np.ndarray
    ) -> List[Tuple[int, int, int, int]]:
        """دۆزینەوەی وردی ناوچەی ڕووخسار بە Haar Cascade + پشتڕاستکردنەوەی پێکهاتە."""
        h, w = frame.shape[:2]
        if h < 40 or w < 40:
            return []

        if self._face_cascade is not None:
            gray = _cv2.cvtColor(frame, _cv2.COLOR_BGR2GRAY)
            gray = _cv2.equalizeHist(gray)
            min_sz = max(36, int(min(w, h) * 0.08))
            rects = self._face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.15,
                minNeighbors=5,
                minSize=(min_sz, min_sz),
            )
            if len(rects) > 0:
                sorted_rects = sorted(
                    [(int(x), int(y), int(bw), int(bh)) for (x, y, bw, bh) in rects],
                    key=lambda r: r[2] * r[3],
                    reverse=True,
                )
                return sorted_rects[:6]

        # ڕێگای یەدەگ: شیکاری ڕەنگی پێست + چڕیی وردەکارییەکانی ڕووخسار (چاو و دەم)
        ycrcb = _cv2.cvtColor(frame, _cv2.COLOR_BGR2YCrCb)
        lower_skin = np.array([0, 133, 77], dtype=np.uint8)
        upper_skin = np.array([255, 173, 127], dtype=np.uint8)
        mask = _cv2.inRange(ycrcb, lower_skin, upper_skin)

        kernel = np.ones((5, 5), dtype=np.uint8)
        mask = _cv2.morphologyEx(mask, _cv2.MORPH_OPEN, kernel)
        mask = _cv2.morphologyEx(mask, _cv2.MORPH_CLOSE, kernel)

        contours_info = _cv2.findContours(
            mask, _cv2.RETR_EXTERNAL, _cv2.CHAIN_APPROX_SIMPLE
        )
        contours = contours_info[0] if len(contours_info) == 2 else contours_info[1]

        min_area = max(1600, int((w * h) * 0.01))
        max_area = int((w * h) * 0.42)
        gray_full = _cv2.cvtColor(frame, _cv2.COLOR_BGR2GRAY)
        faces: List[Tuple[int, int, int, int]] = []

        for cnt in contours:
            area = float(_cv2.contourArea(cnt))
            if area < min_area or area > max_area:
                continue
            x, y, bw, bh = _cv2.boundingRect(cnt)
            aspect = float(bh) / float(max(bw, 1))
            if 0.85 <= aspect <= 1.95:
                face_h = min(bh, int(bw * 1.32))
                roi = gray_full[y : y + face_h, x : x + bw]
                edges = _cv2.Canny(roi, 50, 140)
                edge_density = float(np.count_nonzero(edges)) / float(max(1, roi.size))
                if 0.04 <= edge_density <= 0.35:
                    faces.append((int(x), int(y), int(bw), int(face_h)))

        return faces[:5]

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
                label_txt = f"FACE: {target_name}"

            _cv2.rectangle(frame, (x, y), (x + w, y + h), box_color, 2)
            banner_w = max(w, len(label_txt) * 9 + 16)
            _cv2.rectangle(
                frame, (x, max(0, y - 24)), (x + banner_w, y), (15, 23, 42), -1
            )
            _cv2.putText(
                frame,
                label_txt,
                (x + 5, max(15, y - 6)),
                _cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
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
        """پاشەکەوتکردنی وێنەی تارگێتێکی نوێ لە فۆڵدەری targets/ و نوێکردنەوەی دەستبەجێی گەلەری."""
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


if __name__ == "__main__":
    engine = FaceRecognizerEngine()
    sample = np.zeros((360, 640, 3), dtype=np.uint8)
    _, items = engine.process_frame_with_details(sample)
    print(
        f"[FACE RECOGNIZER] Real Biometric Engine Ready | Targets Loaded: {len(engine._gallery_templates)} | Detections: {len(items)}"
    )
