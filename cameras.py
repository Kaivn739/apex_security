from __future__ import annotations

import os
import threading
import time
from typing import Any, Dict, Optional, Union

import cv2
import numpy as np

_cv2: Any = cv2


class CameraStream:
    """خوێندنەوەی سەربەخۆ و بێ-لاگی فریمەکانی کامێرا (Webcam / Capture Card / RTSP)."""

    def __init__(
        self,
        source: Union[int, str] = 0,
        cam_type: str = "Webcam",
        cam_id: str = "CAM-01",
    ) -> None:
        self.cam_id = cam_id
        self.source: Union[int, str] = source
        self.cam_type = cam_type
        self.running = True
        self.lock = threading.Lock()
        self.frame: Optional[np.ndarray] = None

        self.thread = threading.Thread(target=self._update, daemon=True)
        self.thread.start()

    def _open_capture(self) -> Any:
        if isinstance(self.source, int) or str(self.source).isdigit():
            idx = int(self.source)
            backend = (
                getattr(_cv2, "CAP_DSHOW", 0)
                if os.name == "nt"
                else getattr(_cv2, "CAP_ANY", 0)
            )
            return _cv2.VideoCapture(idx, backend)
        return _cv2.VideoCapture(str(self.source))

    def _update(self) -> None:
        while self.running:
            cap = None
            try:
                cap = self._open_capture()
                if cap is None or not cap.isOpened():
                    time.sleep(0.5)
                    continue

                while self.running and cap.isOpened():
                    ret, raw = cap.read()
                    if (
                        ret
                        and raw is not None
                        and isinstance(raw, np.ndarray)
                        and raw.size > 0
                    ):
                        with self.lock:
                            self.frame = raw
                    else:
                        time.sleep(0.01)
                    time.sleep(0.015)
            except Exception:
                time.sleep(0.5)
            finally:
                if cap is not None:
                    try:
                        cap.release()
                    except Exception:
                        pass

    def get_frame(self) -> Optional[np.ndarray]:
        with self.lock:
            return self.frame.copy() if self.frame is not None else None

    def release(self) -> None:
        self.running = False

    def stop(self) -> None:
        self.running = False


class CameraStreamer(CameraStream):
    """ناوی هاوتا بۆ پشتگیریکردنی مۆدیۆلە کۆنەکان."""

    def __init__(
        self, cam_id_or_source: Any = 0, source: Any = None, cam_type: str = "Webcam"
    ) -> None:
        if source is None:
            super().__init__(source=cam_id_or_source, cam_type=cam_type)
        else:
            super().__init__(
                source=source, cam_type=cam_type, cam_id=str(cam_id_or_source)
            )


class APEXCameraManager:
    def __init__(self, retention_days: int = 90) -> None:
        self.retention_days = retention_days
        self.streamers: Dict[str, CameraStream] = {}

    def get_streamer(
        self, cam_id: str, source: Union[int, str], cam_type: str = "Webcam"
    ) -> CameraStream:
        if cam_id not in self.streamers:
            self.streamers[cam_id] = CameraStream(
                source=source, cam_type=cam_type, cam_id=cam_id
            )
        return self.streamers[cam_id]


if __name__ == "__main__":
    print("[CAMERAS ENGINE] Offline Ready")
