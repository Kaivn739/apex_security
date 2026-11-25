from __future__ import annotations

import os
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import cv2
import numpy as np

_cv2: Any = cv2


class CameraStream:
    """خوێندنەوەی سەربەخۆ و خاوبوونەوەی-سفر (Zero-Lag) بۆ فریمەکانی کامێرا (Webcam / Capture Card / RTSP)."""

    def __init__(
        self,
        source: Union[int, str] = 0,
        cam_type: str = "Webcam",
        cam_id: str = "CAM-01",
        target_fps: int = 30,
    ) -> None:
        self.cam_id = cam_id
        self.source: Union[int, str] = source
        self.cam_type = cam_type
        self.target_fps = max(10, min(60, int(target_fps)))
        self.running = True
        self.connected = False
        self.last_frame_ts = 0.0
        self.fps_actual = 0.0

        self.lock = threading.Lock()
        self.frame: Optional[np.ndarray] = None

        self.thread = threading.Thread(
            target=self._update,
            name=f"APEX-CamStream-{self.cam_id}",
            daemon=True,
        )
        self.thread.start()

    def _open_capture(self) -> Any:
        if isinstance(self.source, int) or str(self.source).isdigit():
            idx = int(self.source)
            backend = (
                getattr(_cv2, "CAP_DSHOW", 0)
                if os.name == "nt"
                else getattr(_cv2, "CAP_ANY", 0)
            )
            cap = _cv2.VideoCapture(idx, backend)
        else:
            os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "rtsp_transport;tcp")
            cap = _cv2.VideoCapture(str(self.source), getattr(_cv2, "CAP_FFMPEG", 0))

        if cap is not None and cap.isOpened():
            try:
                cap.set(_cv2.CAP_PROP_BUFFERSIZE, 1)
                cap.set(_cv2.CAP_PROP_FPS, self.target_fps)
            except Exception:
                pass
        return cap

    def _update(self) -> None:
        frame_counter = 0
        fps_window_start = time.monotonic()

        while self.running:
            cap = None
            try:
                cap = self._open_capture()
                if cap is None or not cap.isOpened():
                    self.connected = False
                    time.sleep(0.4)
                    continue

                self.connected = True
                while self.running and cap.isOpened():
                    # پاککردنەوەی هەر فریمێکی کۆنی بافەر بۆ نەهێشتنی دواکەوتن
                    grabbed = cap.grab()
                    if not grabbed:
                        self.connected = False
                        time.sleep(0.01)
                        break

                    ret, raw = cap.retrieve()
                    if (
                        ret
                        and raw is not None
                        and isinstance(raw, np.ndarray)
                        and raw.size > 0
                    ):
                        now = time.monotonic()
                        with self.lock:
                            self.frame = raw
                            self.last_frame_ts = now

                        frame_counter += 1
                        elapsed = now - fps_window_start
                        if elapsed >= 1.0:
                            self.fps_actual = round(frame_counter / elapsed, 1)
                            frame_counter = 0
                            fps_window_start = now
                    else:
                        time.sleep(0.005)
            except Exception:
                self.connected = False
                time.sleep(0.4)
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
        """گەڕاندنەوەی فریمێکی قەبارە-گونجاو بۆ پشکنینی خێرای AI بەبێ خاوکردنەوەی ڤیدیۆی سەرەکی."""
        with self.lock:
            if self.frame is None:
                return None
            src = self.frame.copy()

        h, w = src.shape[:2]
        if w > max_width and max_width > 0:
            scale = max_width / float(w)
            new_h = max(1, int(h * scale))
            return _cv2.resize(src, (max_width, new_h), interpolation=_cv2.INTER_LINEAR)
        return src

    def is_healthy(self, max_stale_sec: float = 2.0) -> bool:
        if not self.connected or self.last_frame_ts <= 0.0:
            return False
        return (time.monotonic() - self.last_frame_ts) <= max_stale_sec

    def release(self) -> None:
        self.running = False

    def stop(self) -> None:
        self.running = False


class AsyncAIWorker:
    """
    بزوێنەری شیکارکردنی AI لە پاشبنەما (Background Thread):
    فریمەکانی پشکنین بە سەربەخۆیی شیکار دەکات تا پەخشی زیندووی کامێرا هەرگیز خاو نەبێتەوە.
    """

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
            name=f"APEX-AIWorker-{self.cam_id}",
            daemon=True,
        )
        self._thread.start()

    def submit_frame(self, frame: np.ndarray) -> None:
        """ناردنی نوێترین فریم بۆ شیکارکردن (ئەگەر شیکارکەر سەرقاڵ بێت فریمە کۆنەکە دەگۆڕێت بە نوێیەکە)."""
        with self._lock:
            self._pending_frame = frame.copy()
        self._event.set()

    def _worker_loop(self) -> None:
        while self.running:
            triggered = self._event.wait(timeout=0.2)
            if not self.running:
                break
            if not triggered:
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
        self, max_age_sec: float = 1.2
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

    def stop_all(self) -> None:
        for stream in self.streamers.values():
            stream.stop()
        self.streamers.clear()


if __name__ == "__main__":
    print("[CAMERAS ENGINE] Zero-Lag Multi-Threaded Engine Ready")
