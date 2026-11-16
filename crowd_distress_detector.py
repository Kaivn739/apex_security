from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

try:
    from apex_internal_core import InternalEvent, get_internal_cpu

    _HAS_INTERNAL_CORE = True
except ImportError:
    InternalEvent = None  # type: ignore[assignment,misc]
    get_internal_cpu = None  # type: ignore[assignment]
    _HAS_INTERNAL_CORE = False


class CrowdDistressDetector:
    """
    مۆدیۆلی سەربەخۆی ناسینەوەی قەرەباڵغی و جوڵەی لەناکاوی هاوارکردن (100% Offline):
    - بە تەواوی لەسەر فەنکشنە بنەڕەتییەکانی OpenCV + NumPy کار دەکات (بێ هیچ بارگرانییەک لەسەر CPU).
    1. ژماردنی قەرەباڵغی (Crowd Density) بە مۆدێلی پاشخانی خێرا.
    2. ناسینەوەی جوڵەی لەناکاوی داوای هاریکاری / شڵەژان (Sudden Panic / Distress Burst).
    """

    def __init__(
        self, crowd_threshold: int = 5, panic_motion_ratio: float = 0.14
    ) -> None:
        self.crowd_threshold: int = int(crowd_threshold)
        self.panic_motion_ratio: float = float(panic_motion_ratio)
        self._prev_gray: Optional[np.ndarray] = None
        self._bg_model: Optional[np.ndarray] = None

    def process_frame(
        self,
        frame: np.ndarray,
        camera_id: str = "CAM-01",
        emit_events: bool = True,
    ) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
        """شیکاریی فریم بۆ قەرەباڵغی یان جوڵەی لەناکاوی داوای هاریکاری."""
        if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
            return frame, []

        output: np.ndarray = frame.copy()
        detections: List[Dict[str, Any]] = []

        # بچووککردنەوەی فریم بۆ خێرایی بەرز لەسەر CPU
        h_orig: int = int(output.shape[0])
        w_orig: int = int(output.shape[1])
        scale: float = 480.0 / float(max(w_orig, 1))
        resized_w: int = max(160, int(w_orig * scale))
        resized_h: int = max(120, int(h_orig * scale))

        small = cv2.resize(output, (resized_w, resized_h))
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        inv_scale: float = 1.0 / scale

        # ١. ژماردنی قەرەباڵغی (Crowd Density) بە گۆڕاوی ناوخۆیی (بێ کێشەی پارامێتەر)
        person_boxes: List[Tuple[int, int, int, int]] = []
        gray_float: np.ndarray = np.asarray(gray, dtype=np.float32)
        bg_model: Optional[np.ndarray] = self._bg_model

        if bg_model is None or bg_model.shape != gray_float.shape:
            self._bg_model = gray_float.copy()
        else:
            bg_uint8: np.ndarray = np.asarray(bg_model, dtype=np.uint8)
            fg_diff = cv2.absdiff(bg_uint8, gray)
            _, fg_mask = cv2.threshold(fg_diff, 30.0, 255.0, cv2.THRESH_BINARY)
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)

            contours, _ = cv2.findContours(
                fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            max_person_area: float = float(resized_w * resized_h) * 0.45
            for cnt in contours:
                area: float = float(cv2.contourArea(cnt))
                if 350.0 <= area <= max_person_area:
                    x, y, w, h = cv2.boundingRect(cnt)
                    if h >= int(w * 0.8):
                        person_boxes.append((int(x), int(y), int(w), int(h)))

            blended_bg = cv2.addWeighted(bg_model, 0.95, gray_float, 0.05, 0.0)
            self._bg_model = np.asarray(blended_bg, dtype=np.float32)

        people_count: int = len(person_boxes)
        for x, y, w, h in person_boxes:
            rx: int = int(x * inv_scale)
            ry: int = int(y * inv_scale)
            rw: int = int(w * inv_scale)
            rh: int = int(h * inv_scale)
            cv2.rectangle(output, (rx, ry), (rx + rw, ry + rh), (255, 200, 0), 2)

        if people_count >= self.crowd_threshold:
            crowd_conf: float = min(96.0, round(70.0 + float(people_count) * 3.0, 1))
            detections.append(
                {
                    "type": "CROWD_SURGE",
                    "people_count": people_count,
                    "confidence": crowd_conf,
                    "camera_id": camera_id,
                }
            )
            cv2.putText(
                output,
                f"CROWD ALERT: {people_count} PERSONS",
                (16, 36),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.75,
                (0, 165, 255),
                2,
            )

        # ٢. پشکنینی جوڵەی لەناکاوی داوای هاریکاری / شڵەژان
        prev_gray: Optional[np.ndarray] = self._prev_gray
        if prev_gray is not None and prev_gray.shape == gray.shape:
            diff = cv2.absdiff(prev_gray, gray)
            _, thresh = cv2.threshold(diff, 35.0, 255.0, cv2.THRESH_BINARY)
            active_pixels: int = int(np.count_nonzero(thresh))
            total_pixels: int = int(thresh.size)
            motion_ratio: float = float(active_pixels) / float(max(total_pixels, 1))

            if motion_ratio >= self.panic_motion_ratio:
                contours, _ = cv2.findContours(
                    thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
                )
                largest_cnt: Optional[np.ndarray] = None
                max_area: float = 600.0
                for cnt in contours:
                    c_area: float = float(cv2.contourArea(cnt))
                    if c_area > max_area:
                        max_area = c_area
                        largest_cnt = cnt

                if largest_cnt is not None:
                    lx, ly, lw, lh = cv2.boundingRect(largest_cnt)
                    drx: int = int(lx * inv_scale)
                    dry: int = int(ly * inv_scale)
                    drw: int = int(lw * inv_scale)
                    drh: int = int(lh * inv_scale)
                    distress_conf: float = min(
                        94.0, round(65.0 + motion_ratio * 100.0, 1)
                    )
                    detections.append(
                        {
                            "type": "EMERGENCY_DISTRESS_MOTION",
                            "motion_ratio": round(motion_ratio, 3),
                            "confidence": distress_conf,
                            "bbox": (drx, dry, drw, drh),
                            "camera_id": camera_id,
                        }
                    )
                    cv2.rectangle(
                        output, (drx, dry), (drx + drw, dry + drh), (0, 0, 255), 2
                    )
                    cv2.putText(
                        output,
                        f"DISTRESS / PANIC {distress_conf}%",
                        (drx, max(22, dry - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0, 0, 255),
                        2,
                    )

        self._prev_gray = np.asarray(gray, dtype=np.uint8)

        # ٣. ناردنی ئاگاداری بۆ CPU ناوخۆیی
        if (
            detections
            and emit_events
            and _HAS_INTERNAL_CORE
            and get_internal_cpu is not None
            and InternalEvent is not None
        ):
            top = detections[0]
            get_internal_cpu().dispatch_event(
                InternalEvent(
                    event_type="CROWD_DISTRESS",
                    camera_id=camera_id,
                    severity="HIGH",
                    title=f"{top['type']} ({top['confidence']}%)",
                    details={"detections": detections, "people_count": people_count},
                )
            )

        return output, detections


if __name__ == "__main__":
    detector = CrowdDistressDetector(crowd_threshold=3, panic_motion_ratio=0.10)
    f1 = np.zeros((360, 640, 3), dtype=np.uint8)
    f2 = np.zeros((360, 640, 3), dtype=np.uint8)
    cv2.rectangle(f2, (120, 80), (480, 300), (255, 255, 255), -1)
    detector.process_frame(f1, camera_id="CAM-03", emit_events=False)
    _, found = detector.process_frame(f2, camera_id="CAM-03", emit_events=False)
    print(
        f"[CROWD & DISTRESS DETECTOR] Offline Ready | Detections: {len(found)} | Details: {found}"
    )
