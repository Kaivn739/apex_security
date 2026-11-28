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
    مۆدیۆلی وردی ناسینەوەی چەک و بڵێسەی تەقە (بەبێ ئاگاداریی هەڵە لە تەنی ئاسایی):
    - ئەگەر مۆدێلی فێرکراوی models/weapon.pt هەبێت، ڕاستەوخۆ چەک دەناسێتەوە.
    - ئەگەر مۆدێلی قورس نەبێت، تەنها پشکنینی بڵێسەی خێرای تەقە (Muzzle Flash) دەکات و
      مۆبایل و چوارچێوەی پەنجەرە بە چەک دانانێت.
    """

    def __init__(self, min_weapon_area: int = 900) -> None:
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
        if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
            return frame, []

        output = frame.copy()
        detections: List[Dict[str, Any]] = []

        # ١. ئەگەر مۆدێلی فێرکراوی چەک هەبوو، تەنها ئەو بەکاربهێنە
        if self._yolo_model is not None:
            try:
                results = self._yolo_model.predict(output, verbose=False, conf=0.62)
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
        else:
            # ٢. پشکنینی بڵێسەی خێرای تەقە (Muzzle Flash Spike) بەبێ ئاگاداریی هەڵە لە تەنی ڕەش
            gray = _cv2.cvtColor(output, _cv2.COLOR_BGR2GRAY)
            mean_bright = float(np.mean(gray))
            prev_bright = self._prev_brightness_by_cam.get(camera_id)

            if prev_bright is not None and (mean_bright - prev_bright) > 55.0:
                _, flash_mask = _cv2.threshold(gray, 248, 255, _cv2.THRESH_BINARY)
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
                    if 150 <= area <= 12000:
                        x, y, w, h = _cv2.boundingRect(cnt)
                        detections.append(
                            {
                                "type": "GUNSHOT_FLASH",
                                "confidence": 91.0,
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
