from __future__ import annotations

import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

_cv2: Any = cv2

try:
    from apex_brain import APEXBrainCore
except Exception:
    APEXBrainCore = None


class ALPREngine:
    """
    بزوێنەری ڕاستەقینەی دۆزینەوە و شیکارکردنی تابلۆی ئۆتۆمبێل (100% Offline, Zero-Lag):
    - دۆزینەوەی ناوچەی تابلۆ لە وێنەدا لە ڕێگەی شیکاری لێوارە ستوونییەکان و ڕێژەی ئەندازەیی (2.0 تا 5.5).
    - پشکنینی خێرای نووسینی تابلۆ (پشتگیری ناوخۆیی بێ پێویستبوون بە ئینتەرنێت).
    - بەستنەوەی راستەوخۆ بە لیستی داواکراوان (SUSPECT / BLACK_LISTED) و عەقڵی APEXBrainCore.
    """

    def __init__(self, offline_only: bool = True) -> None:
        self.offline_only = offline_only
        self.brain = APEXBrainCore() if APEXBrainCore is not None else None

        self.target_database: Dict[str, Dict[str, str]] = {
            "22B-10922": {
                "status": "SUSPECT",
                "owner": "ئیسماعیل زاهیر",
                "severity": "HIGH",
            },
            "89C-04048": {
                "status": "BLACK_LISTED",
                "owner": "مەترسیدار / نەناسراو",
                "severity": "CRITICAL",
            },
            "33V-P377": {
                "status": "AUTHORIZED",
                "owner": "ئۆتۆمبێلی ڕێگەپێدراو",
                "severity": "LOW",
            },
        }
        self.alerted_plates: set[str] = set()
        self._ocr_reader = self._init_optional_offline_ocr()

    def _init_optional_offline_ocr(self) -> Any:
        try:
            import importlib

            return importlib.import_module("pytesseract")
        except Exception:
            return None

    def register_plate(
        self,
        plate_number: str,
        owner: str,
        status: str = "SUSPECT",
        severity: str = "HIGH",
    ) -> None:
        clean = self._normalize_plate(plate_number)
        if clean:
            self.target_database[clean] = {
                "status": status.upper(),
                "owner": owner,
                "severity": severity.upper(),
            }

    @staticmethod
    def _normalize_plate(raw_text: str) -> str:
        cleaned = re.sub(r"[^A-Z0-9\-]", "", (raw_text or "").upper().strip())
        return cleaned

    def evaluate_plate(self, plate_number: str) -> Dict[str, str]:
        plate_clean = self._normalize_plate(plate_number)
        if plate_clean in self.target_database:
            info = self.target_database[plate_clean]
            if (
                info["status"] in {"SUSPECT", "BLACK_LISTED"}
                and plate_clean not in self.alerted_plates
            ):
                if self.brain is not None and hasattr(self.brain, "log_alert"):
                    try:
                        self.brain.log_alert(plate_clean, info["owner"], info["status"])
                    except Exception:
                        pass
                self.alerted_plates.add(plate_clean)
            return info

        return {
            "status": "AUTHORIZED",
            "owner": "عادی / ڕێگەپێدراو",
            "severity": "NONE",
        }

    def _detect_plate_candidates(
        self, frame: np.ndarray
    ) -> List[Tuple[int, int, int, int]]:
        """دۆزینەوەی ناوچە لاکێشەییەکانی تابلۆی ئۆتۆمبێل بە خێراییەکی بەرز."""
        h, w = frame.shape[:2]
        if h < 60 or w < 100:
            return []

        gray = _cv2.cvtColor(frame, _cv2.COLOR_BGR2GRAY)
        blur = _cv2.bilateralFilter(gray, 9, 55, 55)

        rect_kernel = _cv2.getStructuringElement(_cv2.MORPH_RECT, (17, 5))
        blackhat = _cv2.morphologyEx(blur, _cv2.MORPH_BLACKHAT, rect_kernel)

        grad_x = _cv2.Sobel(blackhat, ddepth=_cv2.CV_32F, dx=1, dy=0, ksize=3)
        grad_x = np.absolute(grad_x)
        max_val = float(np.max(grad_x)) if grad_x.size > 0 else 0.0
        if max_val <= 0:
            return []
        grad_x = (255.0 * (grad_x / max_val)).astype("uint8")

        grad_x = _cv2.GaussianBlur(grad_x, (5, 5), 0)
        grad_x = _cv2.morphologyEx(grad_x, _cv2.MORPH_CLOSE, rect_kernel)
        _, thresh = _cv2.threshold(
            grad_x, 0, 255, _cv2.THRESH_BINARY | _cv2.THRESH_OTSU
        )

        thresh = _cv2.erode(thresh, None, iterations=1)
        thresh = _cv2.dilate(thresh, None, iterations=2)

        contours_info = _cv2.findContours(
            thresh, _cv2.RETR_EXTERNAL, _cv2.CHAIN_APPROX_SIMPLE
        )
        contours = contours_info[0] if len(contours_info) == 2 else contours_info[1]

        min_area = max(900, int((w * h) * 0.0025))
        max_area = int((w * h) * 0.18)
        candidates: List[Tuple[int, int, int, int]] = []

        for cnt in contours:
            area = float(_cv2.contourArea(cnt))
            if area < min_area or area > max_area:
                continue
            x, y, bw, bh = _cv2.boundingRect(cnt)
            if bh <= 0:
                continue
            aspect = float(bw) / float(bh)
            # ڕێژەی پانی بۆ بەرزی تابلۆی عێراق/هەرێم و ستاندارد (نێوان 1.9 تا 5.6)
            if 1.9 <= aspect <= 5.6 and bw >= 65 and bh >= 16:
                roi = gray[y : y + bh, x : x + bw]
                contrast = float(np.std(roi))
                if contrast >= 28.0:
                    candidates.append((int(x), int(y), int(bw), int(bh)))

        candidates.sort(key=lambda b: b[2] * b[3], reverse=True)
        return candidates[:4]

    def _read_plate_roi(self, roi_bgr: np.ndarray) -> Optional[str]:
        """خوێندنەوەی ژمارە و پیتی ناو تابلۆ ئەگەر OCRـی ناوخۆیی بەردەست بێت."""
        if self._ocr_reader is None or roi_bgr is None or roi_bgr.size == 0:
            return None
        try:
            gray = _cv2.cvtColor(roi_bgr, _cv2.COLOR_BGR2GRAY)
            up = _cv2.resize(
                gray, (0, 0), fx=2.0, fy=2.0, interpolation=_cv2.INTER_CUBIC
            )
            _, bin_img = _cv2.threshold(
                up, 0, 255, _cv2.THRESH_BINARY + _cv2.THRESH_OTSU
            )
            raw_txt = self._ocr_reader.image_to_string(
                bin_img,
                config="--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-",
            )
            norm = self._normalize_plate(raw_txt)
            return norm if len(norm) >= 5 else None
        except Exception:
            return None

    def process_frame(
        self, frame: np.ndarray, camera_id: str = "CAM-02"
    ) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
        if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
            return frame, []

        detections: List[Dict[str, Any]] = []
        boxes = self._detect_plate_candidates(frame)

        for x, y, w, h in boxes:
            roi = frame[y : y + h, x : x + w]
            plate_text = self._read_plate_roi(roi)

            if plate_text:
                info = self.evaluate_plate(plate_text)
                status = info["status"]
                is_threat = status in {"SUSPECT", "BLACK_LISTED"}
                color = (0, 0, 255) if is_threat else (0, 255, 0)
                label = f"PLATE: {plate_text} [{status}]"
            else:
                plate_text = "PLATE_REGION"
                status = "DETECTED"
                color = (56, 189, 248)
                label = f"PLATE ZONE ({w}x{h})"

            _cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            banner_w = max(w, len(label) * 9 + 14)
            _cv2.rectangle(
                frame, (x, max(0, y - 22)), (x + banner_w, y), (15, 23, 42), -1
            )
            _cv2.putText(
                frame,
                label,
                (x + 4, max(15, y - 6)),
                _cv2.FONT_HERSHEY_SIMPLEX,
                0.48,
                color,
                2,
            )

            detections.append(
                {
                    "plate": plate_text,
                    "status": status,
                    "camera_id": camera_id,
                    "bbox": (x, y, w, h),
                    "time": time.strftime("%H:%M:%S"),
                }
            )

        return frame, detections


APEXALPRPipeline = ALPREngine


if __name__ == "__main__":
    engine = ALPREngine()
    blank = np.zeros((360, 640, 3), dtype=np.uint8)
    _, found = engine.process_frame(blank)
    print(f"[ALPR ENGINE] 100% Offline Ready | Plates Detected: {len(found)}")
