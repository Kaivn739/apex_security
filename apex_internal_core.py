from __future__ import annotations

import os
import queue
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

try:
    import psutil
except ImportError:
    psutil = None  # type: ignore[assignment]


@dataclass
class InternalEvent:
    """پێکهاتەی ستانداردی هەر ڕووداوێک کە لە بزوێنەرەکانی AIـەوە دەردەچێت."""

    event_type: str  # وەک: FACE_MATCH, ALPR, FIRE_SMOKE, WEAPON, CROWD_DISTRESS
    camera_id: str  # وەک: CAM-01
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    title: str
    details: Dict[str, Any] = field(default_factory=dict)
    snapshot_path: Optional[str] = None
    timestamp: str = field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )


class APEXInternalCPU:
    """
    CPUـی ناوخۆییی سەربەخۆی APEX:
    - پرۆسە قورسەکانی AI لە شاشەی سەرەکی (UI) جیا دەکاتەوە.
    - بەپێی ڕێژەی CPU و RAMـی لاپتۆپەکە خێرایی شیکاری ڕێک دەخات تا کۆمپیوتەر گیر نەبێت.
    - ڕووداوەکان بە خێرایی دەگوازێتەوە بۆ تێلێگرام، GIS، و داتابەیس.
    """

    def __init__(self, max_workers: int = 4, max_queue_size: int = 256) -> None:
        self._max_workers = max(2, min(max_workers, (os.cpu_count() or 4)))
        self._executor = ThreadPoolExecutor(
            max_workers=self._max_workers, thread_name_prefix="APEX_InternalCPU"
        )
        self._event_queue: queue.Queue[InternalEvent] = queue.Queue(
            maxsize=max_queue_size
        )
        self._subscribers: List[Callable[[InternalEvent], None]] = []
        self._lock = threading.Lock()
        self._running = True
        self._processed_tasks = 0
        self._dropped_tasks = 0
        self._start_time = time.time()

        # تێلێگرامی ناوخۆیی و پردی داتابەیس لە پاشخاندا
        self._dispatcher_thread = threading.Thread(
            target=self._event_dispatcher_loop, name="APEX_EventDispatcher", daemon=True
        )
        self._dispatcher_thread.start()

    def get_hardware_metrics(self) -> Dict[str, Any]:
        """پشکنینی ڕاستەوخۆی CPU و RAM بەبێ دروستکردنی هیچ وەستانێک."""
        cpu_pct = 0.0
        ram_pct = 0.0
        if psutil is not None:
            try:
                cpu_pct = float(psutil.cpu_percent(interval=None))
                ram_pct = float(psutil.virtual_memory().percent)
            except Exception:
                cpu_pct = 0.0
                ram_pct = 0.0

        # دیاریکردنی هەنگاوی فریم (Frame Stride) بۆ پاراستنی لاپتۆپ لە گەرمبوون و گیربوون
        if cpu_pct >= 85.0 or ram_pct >= 90.0:
            recommended_stride = 8
            load_state = "THROTTLED_SAFE"
        elif cpu_pct >= 65.0 or ram_pct >= 80.0:
            recommended_stride = 4
            load_state = "BALANCED"
        else:
            recommended_stride = 2
            load_state = "OPTIMAL"

        return {
            "cpu_percent": round(cpu_pct, 1),
            "ram_percent": round(ram_pct, 1),
            "recommended_frame_stride": recommended_stride,
            "load_state": load_state,
            "active_workers": self._max_workers,
            "processed_tasks": self._processed_tasks,
            "dropped_tasks": self._dropped_tasks,
            "uptime_seconds": int(time.time() - self._start_time),
        }

    def should_process_frame(self, frame_index: int) -> bool:
        """بڕیاردان لەسەر ئەوەی ئایا ئەم فریمە شیکاری AIـی لەسەر بکرێت یان تێپەڕێنرێت."""
        metrics = self.get_hardware_metrics()
        stride = int(metrics["recommended_frame_stride"])
        return (frame_index % stride) == 0

    def submit_ai_task(
        self, fn: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> Optional[Future[Any]]:
        """ناردنی ئەرکی AI بۆ ناو CPUـی ناوخۆیی بە شێوازی سەلامەت."""
        if not self._running:
            return None
        try:
            future = self._executor.submit(self._wrapped_task, fn, *args, **kwargs)
            return future
        except Exception:
            with self._lock:
                self._dropped_tasks += 1
            return None

    def _wrapped_task(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        result = fn(*args, **kwargs)
        with self._lock:
            self._processed_tasks += 1
        return result

    def register_event_listener(
        self, listener: Callable[[InternalEvent], None]
    ) -> None:
        """بەستنەوەی مۆدیۆلەکانی تێلێگرام، نەخشەی GIS، و داتابەیس بە CPU ناوخۆییەوە."""
        with self._lock:
            if listener not in self._subscribers:
                self._subscribers.append(listener)

    def dispatch_event(self, event: InternalEvent) -> bool:
        """ناردنی ڕووداوی دۆزراوە (چەک، ئاگر، تارگێت، تابلۆ) بۆ ڕیزبەندیی خێرا."""
        try:
            self._event_queue.put_nowait(event)
            return True
        except queue.Full:
            with self._lock:
                self._dropped_tasks += 1
            return False

    def _event_dispatcher_loop(self) -> None:
        """گەیاندنی خۆکاری ڕووداوەکان بە هەموو مۆدیۆلە بەستراوەکان لە پاشخاندا."""
        while self._running:
            try:
                event = self._event_queue.get(timeout=0.25)
            except queue.Empty:
                continue

            with self._lock:
                listeners = list(self._subscribers)

            for listener in listeners:
                try:
                    listener(event)
                except Exception:
                    # هەڵەی یەک مۆدیۆل نابێت ببێتە هۆی وەستانی CPU ناوخۆیی
                    continue

    def shutdown(self) -> None:
        """داخستنی پاک و بێ کێشەی CPU ناوخۆیی."""
        self._running = False
        self._executor.shutdown(wait=False, cancel_futures=True)


# نوسخەی ناوەندیی هاوبەش بۆ هەموو فایلەکانی پڕۆژەی APEX
_CORE_INSTANCE: Optional[APEXInternalCPU] = None
_CORE_LOCK = threading.Lock()


def get_internal_cpu() -> APEXInternalCPU:
    """وەرگرتنی نوسخەی سەرەکیی CPU ناوخۆیی لە هەر فایلێکی پڕۆژەکەوە."""
    global _CORE_INSTANCE
    with _CORE_LOCK:
        if _CORE_INSTANCE is None:
            _CORE_INSTANCE = APEXInternalCPU()
        return _CORE_INSTANCE


if __name__ == "__main__":
    core = get_internal_cpu()
    received: List[str] = []

    def _test_listener(ev: InternalEvent) -> None:
        received.append(f"{ev.camera_id}:{ev.event_type}")

    core.register_event_listener(_test_listener)
    fut = core.submit_ai_task(lambda x, y: x + y, 10, 25)
    task_res = fut.result(timeout=2.0) if fut else None

    core.dispatch_event(
        InternalEvent(
            event_type="SYSTEM_CHECK",
            camera_id="CAM-01",
            severity="LOW",
            title="Internal CPU Self-Test",
        )
    )
    time.sleep(0.3)
    health = core.get_hardware_metrics()
    print(
        f"[APEX INTERNAL CPU] Task Result: {task_res} | Events: {received} | State: {health['load_state']}"
    )
    core.shutdown()
