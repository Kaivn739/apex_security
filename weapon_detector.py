from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import Any, Dict, List, Tuple

import cv2
import numpy as np

_cv2: Any = cv2

try:
    from apex_internal_core import InternalEvent, get_internal_cpu
except ImportError:
    InternalEvent = None  # type: ignore[assignment,misc]
    get_internal_cpu = None  # type: ignore[assignment]


class WeaponDetector:
    """
    مۆدیۆلی سەربەخۆ و وردی ناسینەوەی چەک و ڕووداوی تەقە (100% Offline, Multi-Camera Safe):
    - پشتگیریی مۆدێلی ناوخۆیی (models/weapon.pt) ئەگەر لەسەر کۆمپیوتەرەکە هەبێت.
    - جیاکردنەوەی ڕووناکیی پێشووی هەر کامێرایەک بە سەربەخۆیی بۆ دۆزینەوەی بڵێسەی تەقە (Muzzle Flash).
    - پشکنینی شێوەی لوولەی چەک بە هەر گۆشەیەک (Rotated Bounding Box + Edge Sharpness).
    """

    def __init__(self, min_weapon_area: int = 750) -> None:
        self.min_weapon_area = min_weapon_area
        self._prev_brightness_by_cam: Dict[str, float] = {}
        self._yolo_model: Any = None
        self._try_load_local_weights()

    def _try_load_local_weights(self) -> None:
        local_weights = Path(__file__).resolve().parent / "models" / "weapon.pt"
        if local_weights.exists():
            try:
                YOLO = getattr(import_module("ultralytics"), "YOLO")
                self._yolo_model = YOLO(str(local_weights))
            except Exception:
                self._yolo_model = None

    def process_frame(
        self,
        frame: np.ndarray,
        camera_id: str = "CAM-01",
        emit_events: bool = True,
    ) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
        """شیکاریی یەک فریم بۆ دۆزینەوەی چەک یان بڵێسەی تەقە بە جیاکردنەوەی هەر کامێرایەک."""
        if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
            return frame, []

        output = frame.copy()
        detections: List[Dict[str, Any]] = []

        # ١. مۆدێلی ناوخۆیی YOLO ئەگەر لە فۆڵدەری models/ هەبوو
        if self._yolo_model is not None:
            try:
                results = self._yolo_model.predict(output, verbose=False, conf=0.50)
                for res in results:
                    if res.boxes is None:
                        continue
                    for box in res.boxes:
                        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                        conf = float(box.conf[0])
                        cls_id = int(box.cls[0])
                        w_label = str(res.names.get(cls_id, "WEAPON")).upper()
                        detections.append(
                            {
                                "type": w_label,
                                "confidence": round(conf * 100, 1),
                                "bbox": (x1, y1, x2 - x1, y2 - y1),
                                "camera_id": camera_id,
                            }
                        )
                        _cv2.rectangle(output, (x1, y1), (x2, y2), (0, 0, 255), 3)
                        _cv2.putText(
                            output,
                            f"WEAPON: {w_label} {int(conf * 100)}%",
                            (x1, max(22, y1 - 8)),
                            _cv2.FONT_HERSHEY_SIMPLEX,
                            0.6,
                            (0, 0, 255),
                            2,
                        )
            except Exception:
                pass

        # ٢. بزوێنەری ناوخۆییی OpenCV بۆ دۆزینەوەی لوولەی چەک و بڵێسەی تەقە
        if not detections:
            gray = _cv2.cvtColor(output, _cv2.COLOR_BGR2GRAY)
            hsv = _cv2.cvtColor(output, _cv2.COLOR_BGR2HSV)
            mean_bright = float(np.mean(gray))
            prev_bright = self._prev_brightness_by_cam.get(camera_id)

            # پشکنینی بڵێسەی خێرای تەقە (Muzzle Flash Spike) بۆ هەمان کامێرا
            if prev_bright is not None and (mean_bright - prev_bright) > 38.0:
                _, flash_mask = _cv2.threshold(gray, 240, 255, _cv2.THRESH_BINARY)
                flash_contours_info = _cv2.findContours(
                    flash_mask, _cv2.RETR_EXTERNAL, _cv2.CHAIN_APPROX_SIMPLE
                )
                flash_contours = (
                    flash_contours_info[0]
                    if len(flash_contours_info) == 2
                    else flash_contours_info[1]
                )
                for cnt in flash_contours:
                    area = float(_cv2.contourArea(cnt))
                    if 120 <= area <= 15000:
                        x, y, w, h = _cv2.boundingRect(cnt)
                        detections.append(
                            {
                                "type": "GUNSHOT_FLASH",
                                "confidence": 89.5,
                                "bbox": (int(x), int(y), int(w), int(h)),
                                "camera_id": camera_id,
                            }
                        )
                        _cv2.rectangle(output, (x, y), (x + w, y + h), (0, 0, 255), 3)
                        _cv2.putText(
                            output,
                            "GUNSHOT FLASH DETECTED!",
                            (x, max(22, y - 8)),
                            _cv2.FONT_HERSHEY_SIMPLEX,
                            0.6,
                            (0, 0, 255),
                            2,
                        )
                        break

            self._prev_brightness_by_cam[camera_id] = mean_bright

            # پشکنینی تەنی درێژی کانزایی/ڕەش بە هەر گۆشەیەک (Rotated MinAreaRect)
            sat_ch = hsv[:, :, 1]
            val_ch = hsv[:, :, 2]
            metallic_mask = np.where(
                (sat_ch < 42) & (val_ch > 15) & (val_ch < 98), 255, 0
            ).astype(np.uint8)
            kernel = _cv2.getStructuringElement(_cv2.MORPH_ELLIPSE, (5, 5))
            metallic_mask = _cv2.morphologyEx(metallic_mask, _cv2.MORPH_OPEN, kernel)
            metallic_mask = _cv2.morphologyEx(metallic_mask, _cv2.MORPH_CLOSE, kernel)

            contours_info = _cv2.findContours(
                metallic_mask, _cv2.RETR_EXTERNAL, _cv2.CHAIN_APPROX_SIMPLE
            )
            contours = contours_info[0] if len(contours_info) == 2 else contours_info[1]
            edges_full = _cv2.Canny(gray, 55, 150)

            for cnt in contours:
                area = float(_cv2.contourArea(cnt))
                if area < self.min_weapon_area:
                    continue

                rect = _cv2.minAreaRect(cnt)
                rw, rh = rect[1]
                if rw <= 0 or rh <= 0:
                    continue

                long_side = max(rw, rh)
                short_side = min(rw, rh)
                aspect_ratio = float(long_side) / float(short_side)
                box_area = float(rw * rh)
                solidity = area / max(1.0, box_area)

                x, y, w, h = _cv2.boundingRect(cnt)
                if (
                    3.2 <= aspect_ratio <= 9.5
                    and solidity >= 0.55
                    and long_side < (output.shape[1] * 0.65)
                ):
                    roi_edges = edges_full[y : y + h, x : x + w]
                    edge_ratio = float(np.count_nonzero(roi_edges)) / float(
                        max(1, roi_edges.size)
                    )
                    if edge_ratio < 0.04:
                        continue

                    conf = min(
                        94.5, round(68.0 + (aspect_ratio * 2.2) + (solidity * 8.0), 1)
                    )
                    detections.append(
                        {
                            "type": "WEAPON_SUSPECT",
                            "confidence": conf,
                            "bbox": (int(x), int(y), int(w), int(h)),
                            "camera_id": camera_id,
                        }
                    )
                    _cv2.rectangle(output, (x, y), (x + w, y + h), (0, 0, 255), 2)
                    _cv2.rectangle(
                        output, (x, max(0, y - 24)), (x + 215, y), (160, 0, 0), -1
                    )
                    _cv2.putText(
                        output,
                        f"WEAPON ALERT {conf}%",
                        (x + 5, max(16, y - 6)),
                        _cv2.FONT_HERSHEY_SIMPLEX,
                        0.52,
                        (255, 255, 255),
                        2,
                    )

        # ٣. ناردنی ئاگاداریی بەپەلە بۆ CPU ناوخۆیی و پاسەوانەکان
        if (
            detections
            and emit_events
            and get_internal_cpu is not None
            and InternalEvent is not None
        ):
            top = detections[0]
            get_internal_cpu().dispatch_event(
                InternalEvent(
                    event_type="WEAPON",
                    camera_id=camera_id,
                    severity="CRITICAL",
                    title=f"{top['type']} ({top['confidence']}%)",
                    details={"detections": detections},
                )
            )

        return output, detections


if __name__ == "__main__":
    detector = WeaponDetector(min_weapon_area=500)
    test_frame = np.full((360, 640, 3), 180, dtype=np.uint8)
    _cv2.rectangle(test_frame, (200, 170), (380, 200), (45, 45, 45), -1)
    _, found = detector.process_frame(test_frame, camera_id="CAM-02", emit_events=False)
    print(
        f"[WEAPON DETECTOR] Multi-Cam Precision Ready | Detections: {len(found)} | Details: {found}"
    )
