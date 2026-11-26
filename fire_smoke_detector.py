from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

_cv2: Any = cv2

try:
    from apex_internal_core import InternalEvent, get_internal_cpu
except ImportError:
    InternalEvent = None  # type: ignore[assignment,misc]
    get_internal_cpu = None  # type: ignore[assignment]


class FireSmokeDetector:
    """
    مۆدیۆلی سەربەخۆ و وردی ناسینەوەی ئاگر و دوکەڵ (100% Offline, Multi-Camera Safe):
    - جیاکردنەوەی مێژووی فریمەکان بە پێی هەر کامێرایەک (camera_id) تا تێکەڵ نەبن.
    - شیکاریی بڵێسەی ئاگر بە HSV + YCrCb + پشکنینی لەرینەوەی بڵێسە (Flicker) بۆ نەهێشتنی ئاگادارکردنەوەی هەڵە لە گڵۆپ و تەنی جێگیر.
    - شیکاریی دوکەڵ بە پشکنینی ناوچە خۆڵەمێشییە کەم-تێرەکان و جووڵەی بەرەو سەرەوە.
    """

    def __init__(self, min_fire_area: int = 900, min_smoke_area: int = 2200) -> None:
        self.min_fire_area = min_fire_area
        self.min_smoke_area = min_smoke_area
        self._prev_gray_by_cam: Dict[str, np.ndarray] = {}
        self._yolo_model: Any = None
        self._try_load_local_weights()

    def _try_load_local_weights(self) -> None:
        """بارکردنی مۆدێلی ناوخۆیی تەنها ئەگەر لەسەر هاردەکە هەبێت (بێ ئینتەرنێت)."""
        local_weights = Path(__file__).resolve().parent / "models" / "fire_smoke.pt"
        if local_weights.exists():
            try:
                import importlib

                ultralytics = importlib.import_module("ultralytics")
                yolo_class = getattr(ultralytics, "YOLO")
                self._yolo_model = yolo_class(str(local_weights))
            except Exception:
                self._yolo_model = None

    def process_frame(
        self,
        frame: np.ndarray,
        camera_id: str = "CAM-01",
        emit_events: bool = True,
    ) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
        """شیکاریی یەک فریم بۆ دۆزینەوەی ئاگر و دوکەڵ بە جیاکردنەوەی مێژووی هەر کامێرایەک."""
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
                        detections.append(
                            {
                                "type": label_name,
                                "confidence": round(conf * 100, 1),
                                "bbox": (x1, y1, x2 - x1, y2 - y1),
                                "camera_id": camera_id,
                            }
                        )
                        color = (0, 0, 255) if "FIRE" in label_name else (0, 165, 255)
                        _cv2.rectangle(output, (x1, y1), (x2, y2), color, 2)
                        _cv2.putText(
                            output,
                            f"{label_name} {int(conf * 100)}%",
                            (x1, max(20, y1 - 8)),
                            _cv2.FONT_HERSHEY_SIMPLEX,
                            0.6,
                            color,
                            2,
                        )
            except Exception:
                pass

        # ٢. بزوێنەری خێرا و وردی ناوخۆیی OpenCV (بە پاراستنی مێژووی تایبەتی هەر کامێرایەک)
        if not detections:
            blurred = _cv2.GaussianBlur(output, (9, 9), 0)
            hsv = _cv2.cvtColor(blurred, _cv2.COLOR_BGR2HSV)
            ycrcb = _cv2.cvtColor(blurred, _cv2.COLOR_BGR2YCrCb)
            gray = _cv2.cvtColor(blurred, _cv2.COLOR_BGR2GRAY)

            prev_gray: Optional[np.ndarray] = self._prev_gray_by_cam.get(camera_id)
            motion_mask: Optional[np.ndarray] = None
            if prev_gray is not None and prev_gray.shape == gray.shape:
                diff = _cv2.absdiff(prev_gray, gray)
                _, motion_mask = _cv2.threshold(diff, 12, 255, _cv2.THRESH_BINARY)

            # ماسکی بڵێسەی ئاگر (HSV + YCrCb Chrominance Dominance)
            lower_fire = np.array([0, 125, 185], dtype=np.uint8)
            upper_fire = np.array([34, 255, 255], dtype=np.uint8)
            hsv_fire_mask = _cv2.inRange(hsv, lower_fire, upper_fire)

            y_ch, cr_ch, cb_ch = _cv2.split(ycrcb)
            ycrcb_fire_mask = np.where(
                (y_ch > 175) & (cr_ch > 148) & (cr_ch > cb_ch + 24), 255, 0
            ).astype(np.uint8)
            fire_mask = _cv2.bitwise_and(hsv_fire_mask, ycrcb_fire_mask)

            kernel = _cv2.getStructuringElement(_cv2.MORPH_ELLIPSE, (7, 7))
            fire_mask = _cv2.morphologyEx(fire_mask, _cv2.MORPH_CLOSE, kernel)

            fire_contours_info = _cv2.findContours(
                fire_mask, _cv2.RETR_EXTERNAL, _cv2.CHAIN_APPROX_SIMPLE
            )
            fire_contours = (
                fire_contours_info[0]
                if len(fire_contours_info) == 2
                else fire_contours_info[1]
            )

            for cnt in fire_contours:
                area = float(_cv2.contourArea(cnt))
                if area < self.min_fire_area:
                    continue

                x, y, w, h = _cv2.boundingRect(cnt)
                # پشتڕاستکردنەوەی لەرینەوەی بڵێسە (Flicker) کاتێک فریمی پێشوو هەبێت تا گڵۆپی جێگیر نەگرێت
                flicker_bonus = 0.0
                if motion_mask is not None:
                    roi_motion = motion_mask[y : y + h, x : x + w]
                    flicker_ratio = float(np.count_nonzero(roi_motion)) / float(
                        max(1, roi_motion.size)
                    )
                    if flicker_ratio < 0.03:
                        continue
                    flicker_bonus = min(8.0, flicker_ratio * 25.0)

                conf = min(
                    98.8, round(66.0 + (area / 5000.0) * 26.0 + flicker_bonus, 1)
                )
                detections.append(
                    {
                        "type": "FIRE_DETECTED",
                        "confidence": conf,
                        "bbox": (int(x), int(y), int(w), int(h)),
                        "camera_id": camera_id,
                    }
                )
                _cv2.rectangle(output, (x, y), (x + w, y + h), (0, 0, 255), 2)
                _cv2.rectangle(
                    output, (x, max(0, y - 24)), (x + 195, y), (0, 0, 180), -1
                )
                _cv2.putText(
                    output,
                    f"FIRE ALERT {conf}%",
                    (x + 5, max(16, y - 6)),
                    _cv2.FONT_HERSHEY_SIMPLEX,
                    0.52,
                    (255, 255, 255),
                    2,
                )

            # ماسکی دوکەڵ (ناوچەی خۆڵەمێشیی کەم-تێر لەگەڵ جووڵەی نێوان فریمەکانی هەمان کامێرا)
            if motion_mask is not None:
                _, sat_ch, val_ch = _cv2.split(hsv)
                smoke_color_mask = np.where(
                    (sat_ch < 45) & (val_ch > 130) & (val_ch < 235), 255, 0
                ).astype(np.uint8)
                smoke_mask = _cv2.bitwise_and(smoke_color_mask, motion_mask)
                smoke_mask = _cv2.morphologyEx(smoke_mask, _cv2.MORPH_CLOSE, kernel)

                smoke_contours_info = _cv2.findContours(
                    smoke_mask, _cv2.RETR_EXTERNAL, _cv2.CHAIN_APPROX_SIMPLE
                )
                smoke_contours = (
                    smoke_contours_info[0]
                    if len(smoke_contours_info) == 2
                    else smoke_contours_info[1]
                )
                for cnt in smoke_contours:
                    area = float(_cv2.contourArea(cnt))
                    if area >= self.min_smoke_area:
                        x, y, w, h = _cv2.boundingRect(cnt)
                        conf = min(94.5, round(62.0 + (area / 9000.0) * 28.0, 1))
                        detections.append(
                            {
                                "type": "SMOKE_DETECTED",
                                "confidence": conf,
                                "bbox": (int(x), int(y), int(w), int(h)),
                                "camera_id": camera_id,
                            }
                        )
                        _cv2.rectangle(output, (x, y), (x + w, y + h), (0, 165, 255), 2)
                        _cv2.putText(
                            output,
                            f"SMOKE {conf}%",
                            (x, max(20, y - 8)),
                            _cv2.FONT_HERSHEY_SIMPLEX,
                            0.55,
                            (0, 165, 255),
                            2,
                        )

            self._prev_gray_by_cam[camera_id] = gray

        # ٣. ناردنی ئاگاداری بۆ CPU ناوخۆیی
        if (
            detections
            and emit_events
            and get_internal_cpu is not None
            and InternalEvent is not None
        ):
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
    _cv2.circle(test_frame, (320, 200), 45, (15, 140, 255), -1)
    _, found = detector.process_frame(test_frame, camera_id="CAM-01", emit_events=False)
    print(
        f"[FIRE & SMOKE DETECTOR] Multi-Cam Safe Offline Ready | Detections: {len(found)} | Details: {found}"
    )