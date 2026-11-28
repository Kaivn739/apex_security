from __future__ import annotations

import os
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import cv2
import numpy as np

_cv2: Any = cv2


class CameraStream:
    """خوێندنەوەی سادە، ڕاستەوخۆ و بێ کێشەی وێبکامی ویندۆز و RTSP."""

    def __init__(
        self,
        source: Union[int, str] = 0,
        cam_type: str = "Webcam",
        cam_id: str = "CAM-01",
        target_fps: int = 24,
    ) -> None:
        self.cam_id = cam_id
        self.source: Union[int, str] = source
        self.cam_type = cam_type
        self.running = True
        self.connected = False
        self.last_frame_ts = 0.0
        self.lock = threading.Lock()
        self.frame: Optional[np.ndarray] = None

        self.thread = threading.Thread(
            target=self._update,
            name=f"APEX-Cam-{self.cam_id}",
            daemon=True,
        )
        self.thread.start()

    def _open_capture(self) -> Any:
        if isinstance(self.source, int) or str(self.source).isdigit():
            return _cv2.VideoCapture(int(self.source))
        os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "rtsp_transport;tcp")
        return _cv2.VideoCapture(str(self.source), getattr(_cv2, "CAP_FFMPEG", 0))

    def _update(self) -> None:
        while self.running:
            cap = None
            try:
                cap = self._open_capture()
                if cap is None or not cap.isOpened():
                    self.connected = False
                    time.sleep(0.3)
                    continue

                self.connected = True
                while self.running and cap.isOpened():
                    ret, raw = cap.read()
                    if ret and raw is not None and raw.size > 0:
                        with self.lock:
                            self.frame = raw
                            self.last_frame_ts = time.monotonic()
                        time.sleep(0.02)
                    else:
                        time.sleep(0.04)
            except Exception:
                self.connected = False
                time.sleep(0.3)
            finally:
                self.connected = False
                if cap is not None:
                    try:
                        cap.release()
                    except Exception:
                        pass

    def get_frame(self, copy: bool = True) -> Optional[np.ndarray]:
        with self.lock:
            if self.frame is None:
                return None
            return self.frame.copy() if copy else self.frame

    def get_ai_frame(self, max_width: int = 640) -> Optional[np.ndarray]:
        return self.get_frame(copy=True)

    def is_healthy(self, max_stale_sec: float = 2.0) -> bool:
        return (
            self.connected and (time.monotonic() - self.last_frame_ts) <= max_stale_sec
        )

    def release(self) -> None:
        self.running = False

    def stop(self) -> None:
        self.running = False


class AsyncAIWorker:
    """بزوێنەری سووکی شیکارکردنی AI لە پاشبنەما."""

    def __init__(
        self,
        cam_id: str,
        analyzer_fn: Callable[[np.ndarray], Tuple[np.ndarray, List[str]]],
    ) -> None:
        self.cam_id = cam_id
        self.analyzer_fn = analyzer_fn
        self.running = True
        self._lock = threading.Lock()
        self._pending_frame: Optional[np.ndarray] = None
        self._latest_annotated: Optional[np.ndarray] = None
        self._latest_alerts: List[str] = []
        self._latest_ts: float = 0.0
        self._event = threading.Event()

        self._thread = threading.Thread(
            target=self._worker_loop,
            name=f"APEX-Worker-{self.cam_id}",
            daemon=True,
        )
        self._thread.start()

    def submit_frame(self, frame: np.ndarray) -> None:
        with self._lock:
            self._pending_frame = frame.copy()
        self._event.set()

    def _worker_loop(self) -> None:
        while self.running:
            if not self._event.wait(timeout=0.2):
                continue
            self._event.clear()
            with self._lock:
                work_frame = self._pending_frame
                self._pending_frame = None
            if work_frame is None:
                continue
            try:
                annotated, alerts = self.analyzer_fn(work_frame)
                with self._lock:
                    self._latest_annotated = annotated
                    self._latest_alerts = list(alerts)
                    self._latest_ts = time.monotonic()
            except Exception:
                pass

    def get_latest_result(
        self, max_age_sec: float = 2.5
    ) -> Tuple[Optional[np.ndarray], List[str]]:
        with self._lock:
            if self._latest_annotated is None:
                return None, []
            if (time.monotonic() - self._latest_ts) > max_age_sec:
                return None, []
            return self._latest_annotated.copy(), list(self._latest_alerts)

    def stop(self) -> None:
        self.running = False
        self._event.set()


class CameraStreamer(CameraStream):
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

    def stop_all(self) -> None:
        for stream in self.streamers.values():
            stream.stop()
        self.streamers.clear()
