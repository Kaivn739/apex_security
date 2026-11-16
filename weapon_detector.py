from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

try:
    from apex_internal_core import InternalEvent, get_internal_cpu
except ImportError:
    InternalEvent = None  # type: ignore[assignment,misc]
    get_internal_cpu = None  # type: ignore[assignment]


class WeaponDetector:
    """
    مۆدیۆلی سەربەخۆی ناسینەوەی چەک و ڕووداوی تەقە (100% Offline):
    - پشتگیریی مۆدێلی ناوخۆیی (models/weapon.pt) ئەگەر لەسەر کۆمپیوتەرەکە هەبێت.
    - شیکاریی شێوە ئەندازەییە درێژە کانزایی/تاریکەکان + بڵێسەی لەناکاوی تەقە (Muzzle Flash).
    """

    def __init__(self, min_weapon_area: int = 750) -> None:
        self.min_weapon_area = min_weapon_area
        self._prev_brightness: Optional[float] = None
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
        """شیکاریی یەک فریم بۆ دۆزینەوەی چەک یان بڵێسەی تەقە."""
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
                        cv2.rectangle(output, (x1, y1), (x2, y2), (0, 0, 255), 3)
                        cv2.putText(
                            output,
                            f"WEAPON: {w_label} {int(conf * 100)}%",
                            (x1, max(22, y1 - 8)),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.6,
                            (0, 0, 255),
                            2,
                        )
            except Exception:
                pass

        # ٢. بزوێنەری ناوخۆییی OpenCV بۆ دۆزینەوەی لوولەی چەک و بڵێسەی تەقە
        if not detections:
            gray = cv2.cvtColor(output, cv2.COLOR_BGR2GRAY)
            hsv = cv2.cvtColor(output, cv2.COLOR_BGR2HSV)
            mean_bright = float(np.mean(gray))

            # پشکنینی بڵێسەی خێرای تەقە (Muzzle Flash Spike)
            if (
                self._prev_brightness is not None
                and (mean_bright - self._prev_brightness) > 38.0
            ):
                _, flash_mask = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY)
                flash_contours, _ = cv2.findContours(
                    flash_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
                )
                for cnt in flash_contours:
                    area = cv2.contourArea(cnt)
                    if 120 <= area <= 15000:
                        x, y, w, h = cv2.boundingRect(cnt)
                        detections.append(
                            {
                                "type": "GUNSHOT_FLASH",
                                "confidence": 89.5,
                                "bbox": (x, y, w, h),
                                "camera_id": camera_id,
                            }
                        )
                        cv2.rectangle(output, (x, y), (x + w, y + h), (0, 0, 255), 3)
                        cv2.putText(
                            output,
                            "GUNSHOT FLASH DETECTED!",
                            (x, max(22, y - 8)),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.6,
                            (0, 0, 255),
                            2,
                        )
                        break

            self._prev_brightness = mean_bright

            # پشکنینی تەنی درێژی کانزایی/ڕەش (Elongated Metallic / Firearm Silhouette)
            sat_ch = hsv[:, :, 1]
            val_ch = hsv[:, :, 2]
            metallic_mask = np.where(
                (sat_ch < 40) & (val_ch > 15) & (val_ch < 95), 255, 0
            ).astype(np.uint8)
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 3))
            metallic_mask = cv2.morphologyEx(metallic_mask, cv2.MORPH_OPEN, kernel)

            contours, _ = cv2.findContours(
                metallic_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area < self.min_weapon_area:
                    continue
                x, y, w, h = cv2.boundingRect(cnt)
                if h == 0:
                    continue
                aspect_ratio = float(w) / float(h)
                # چەک و چەقۆ ڕێژەی درێژی بۆ پانییان بەرزە (لە نێوان 3.2 بۆ 9.5)
                if 3.2 <= aspect_ratio <= 9.5 and w < (output.shape[1] * 0.65):
                    conf = min(92.0, round(68.0 + aspect_ratio * 2.5, 1))
                    detections.append(
                        {
                            "type": "WEAPON_SUSPECT",
                            "confidence": conf,
                            "bbox": (x, y, w, h),
                            "camera_id": camera_id,
                        }
                    )
                    cv2.rectangle(output, (x, y), (x + w, y + h), (0, 0, 255), 2)
                    cv2.rectangle(
                        output, (x, max(0, y - 24)), (x + 215, y), (160, 0, 0), -1
                    )
                    cv2.putText(
                        output,
                        f"WEAPON ALERT {conf}%",
                        (x + 5, max(16, y - 6)),
                        cv2.FONT_HERSHEY_SIMPLEX,
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
    # دروستکردنی شێوەی لوولەی چەکی تاقیکردنەوە (درێژ و کانزایی تاریک)
    cv2.rectangle(test_frame, (200, 170), (380, 200), (45, 45, 45), -1)
    _, found = detector.process_frame(test_frame, camera_id="CAM-02", emit_events=False)
    print(
        f"[WEAPON DETECTOR] Offline Ready | Detections: {len(found)} | Details: {found}"
    )
