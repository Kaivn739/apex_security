from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

try:
    from apex_internal_core import InternalEvent, get_internal_cpu
except ImportError:
    InternalEvent = None  # type: ignore[assignment,misc]
    get_internal_cpu = None  # type: ignore[assignment]


class FireSmokeDetector:
    """
    مۆدیۆلی سەربەخۆی ناسینەوەی ئاگر و دوکەڵ (100% Offline):
    - شیکاریی بڵێسەی ئاگر بە یەکخستنی HSV و YCrCb + جوڵەی کاتیی فریمەکان.
    - شیکاریی دوکەڵ بە پشکنینی ناوچە خۆڵەمێشییە کەم-تێرەکان (Low-Saturation Smoke Plumes).
    - ناردنی ئاگاداریی بەپەلە بۆ CPU ناوخۆیی (apex_internal_core.py).
    """

    def __init__(self, min_fire_area: int = 900, min_smoke_area: int = 2200) -> None:
        self.min_fire_area = min_fire_area
        self.min_smoke_area = min_smoke_area
        self._prev_gray: Optional[np.ndarray] = None
        self._yolo_model: Any = None
        self._try_load_local_weights()

    def _try_load_local_weights(self) -> None:
        """بارکردنی مۆدێلی ناوخۆیی تەنها ئەگەر لەسەر هاردەکە هەبێت (بێ ئینتەرنێت)."""
        local_weights = Path(__file__).resolve().parent / "models" / "fire_smoke.pt"
        if local_weights.exists():
            try:
                from ultralytics import YOLO  # type: ignore[import-not-found]
                self._yolo_model = YOLO(str(local_weights))
            except Exception:
                self._yolo_model = None

    def process_frame(
        self,
        frame: np.ndarray,
        camera_id: str = "CAM-01",
        emit_events: bool = True,
    ) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
        """شیکاریی یەک فریم بۆ دۆزینەوەی ئاگر و دوکەڵ."""
        if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
            return frame, []

        output = frame.copy()
        detections: List[Dict[str, Any]] = []

        # ١. ئەگەر مۆدێلی ناوخۆیی YOLO هەبوو، سەرەتا ئەو بەکاربهێنە
        if self._yolo_model is not None:
            try:
                results = self._yolo_model.predict(output, verbose=False, conf=0.45)
                for res in results:
                    if res.boxes is None:
                        continue
                    for box in res.boxes:
                        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                        conf = float(box.conf[0])
                        cls_id = int(box.cls[0])
                        label_name = str(res.names.get(cls_id, "FIRE")).upper()
                        detections.append({
                            "type": label_name,
                            "confidence": round(conf * 100, 1),
                            "bbox": (x1, y1, x2 - x1, y2 - y1),
                            "camera_id": camera_id,
                        })
                        color = (0, 0, 255) if "FIRE" in label_name else (0, 165, 255)
                        cv2.rectangle(output, (x1, y1), (x2, y2), color, 2)
                        cv2.putText(
                            output,
                            f"{label_name} {int(conf * 100)}%",
                            (x1, max(20, y1 - 8)),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.6,
                            color,
                            2,
                        )
            except Exception:
                pass

        # ٢. بزوێنەری خێرای ناوخۆییی OpenCV (کار دەکات لە هەموو بارودۆخێکی ئۆفلایندا)
        if not detections:
            blurred = cv2.GaussianBlur(output, (11, 11), 0)
            hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
            ycrcb = cv2.cvtColor(blurred, cv2.COLOR_BGR2YCrCb)
            gray = cv2.cvtColor(blurred, cv2.COLOR_BGR2GRAY)

            # ماسکی بڵێسەی ئاگر (ڕەنگی سوور/نارنجی/زەردی ڕووناک + Cr بەرزتر لە Cb)
            lower_fire = np.array([0, 120, 185], dtype=np.uint8)
            upper_fire = np.array([35, 255, 255], dtype=np.uint8)
            hsv_fire_mask = cv2.inRange(hsv, lower_fire, upper_fire)

            y_ch, cr_ch, cb_ch = cv2.split(ycrcb)
            ycrcb_fire_mask = np.where((y_ch > 170) & (cr_ch > 145) & (cr_ch > cb_ch + 20), 255, 0).astype(np.uint8)
            fire_mask = cv2.bitwise_and(hsv_fire_mask, ycrcb_fire_mask)

            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
            fire_mask = cv2.morphologyEx(fire_mask, cv2.MORPH_CLOSE, kernel)

            fire_contours, _ = cv2.findContours(fire_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for cnt in fire_contours:
                area = cv2.contourArea(cnt)
                if area >= self.min_fire_area:
                    x, y, w, h = cv2.boundingRect(cnt)
                    conf = min(98.5, round(65.0 + (area / 5000.0) * 30.0, 1))
                    detections.append({
                        "type": "FIRE_DETECTED",
                        "confidence": conf,
                        "bbox": (x, y, w, h),
                        "camera_id": camera_id,
                    })
                    cv2.rectangle(output, (x, y), (x + w, y + h), (0, 0, 255), 2)
                    cv2.rectangle(output, (x, max(0, y - 24)), (x + 190, y), (0, 0, 180), -1)
                    cv2.putText(
                        output,
                        f"FIRE ALERT {conf}%",
                        (x + 5, max(16, y - 6)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.52,
                        (255, 255, 255),
                        2,
                    )

            # ماسکی دوکەڵ (ناوچەی خۆڵەمێشیی کەم-تێر لەگەڵ جوڵەی نێوان فریمەکان)
            if self._prev_gray is not None and self._prev_gray.shape == gray.shape:
                diff = cv2.absdiff(self._prev_gray, gray)
                _, motion_mask = cv2.threshold(diff, 14, 255, cv2.THRESH_BINARY)
                _, sat_ch, val_ch = cv2.split(hsv)
                smoke_color_mask = np.where((sat_ch < 45) & (val_ch > 130) & (val_ch < 235), 255, 0).astype(np.uint8)
                smoke_mask = cv2.bitwise_and(smoke_color_mask, motion_mask)
                smoke_mask = cv2.morphologyEx(smoke_mask, cv2.MORPH_CLOSE, kernel)

                smoke_contours, _ = cv2.findContours(smoke_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                for cnt in smoke_contours:
                    area = cv2.contourArea(cnt)
                    if area >= self.min_smoke_area:
                        x, y, w, h = cv2.boundingRect(cnt)
                        conf = min(94.0, round(60.0 + (area / 9000.0) * 30.0, 1))
                        detections.append({
                            "type": "SMOKE_DETECTED",
                            "confidence": conf,
                            "bbox": (x, y, w, h),
                            "camera_id": camera_id,
                        })
                        cv2.rectangle(output, (x, y), (x + w, y + h), (0, 165, 255), 2)
                        cv2.putText(
                            output,
                            f"SMOKE {conf}%",
                            (x, max(20, y - 8)),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.55,
                            (0, 165, 255),
                            2,
                        )

            self._prev_gray = gray

        # ٣. ناردنی ئاگاداری بۆ CPU ناوخۆیی
        if detections and emit_events and get_internal_cpu is not None and InternalEvent is not None:
            top = detections[0]
            get_internal_cpu().dispatch_event(
                InternalEvent(
                    event_type="FIRE_SMOKE",
                    camera_id=camera_id,
                    severity="CRITICAL",
                    title=f"{top['type']} ({top['confidence']}%)",
                    details={"detections": detections},
                )
            )

        return output, detections


if __name__ == "__main__":
    detector = FireSmokeDetector(min_fire_area=400)
    test_frame = np.zeros((360, 640, 3), dtype=np.uint8)
    # دروستکردنی بڵێسەی تاقیکردنەوە (BGR: شینی کەم، سەوزی مامناوەند، سووری بەرز)
    cv2.circle(test_frame, (320, 200), 45, (15, 140, 255), -1)
    _, found = detector.process_frame(test_frame, camera_id="CAM-01", emit_events=False)
    print(f"[FIRE & SMOKE DETECTOR] Offline Ready | Detections: {len(found)} | Details: {found}")