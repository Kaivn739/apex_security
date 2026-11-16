import time
import shutil
import traceback
import threading
from datetime import datetime
from pathlib import Path


class APEXStorageGuard:
    """
    💾 پاسەوانی بیرگەی هارد:
    ڕێگری دەکات لە پڕبوونی دیسک و داڕمانی سیستەمەکە
    """

    def __init__(self, target_path: str = ".", min_free_gb: float = 20.0):
        self.target_path = Path(target_path).resolve()
        self.min_free_gb = float(min_free_gb)

    def check_storage_health(self) -> dict:
        total, used, free = shutil.disk_usage(self.target_path)
        free_gb = round(free / (1024**3), 2)
        total_gb = round(total / (1024**3), 2)
        used_gb = round(used / (1024**3), 2)

        can_record = free_gb > self.min_free_gb
        return {
            "status": "HEALTHY" if can_record else "CRITICAL_STOP_RECORDING",
            "can_record": can_record,
            "free_gb": free_gb,
            "used_gb": used_gb,
            "total_gb": total_gb,
            "min_threshold_gb": self.min_free_gb,
            "message": (
                f"✅ بیرگە ئاساییە ({free_gb} GB بەتاڵە)"
                if can_record
                else f"🚨 تۆمارکردن ڕاگیرا! بیرگەی بەتاڵ ({free_gb} GB) لە سنووری ({self.min_free_gb} GB) کەمترە"
            ),
        }


class APEXSmartAISampler:
    """
    ⚡ ڕێکخەری زیرەکی خێرایی AI (Smart AI FPS Governor):
    پەخشی کامێرا بە نەرمی دەهێڵێتەوە و شیکاریی AI لەسەر target_ai_fps ڕێکدەخات تا CPU بارگران نەبێت
    """

    def __init__(self, target_ai_fps: float = 10.0):
        self.target_ai_fps = max(1.0, float(target_ai_fps))
        self.min_interval = 1.0 / self.target_ai_fps
        self.last_ai_run: dict = {}
        self.ai_fps_counters: dict = {}
        self._lock = threading.Lock()

    def should_run_ai(self, cam_id) -> bool:
        now = time.time()
        with self._lock:
            last_time = self.last_ai_run.get(cam_id, 0.0)
            if (now - last_time) >= self.min_interval:
                elapsed = max(0.001, now - last_time)
                self.ai_fps_counters[cam_id] = (
                    round(1.0 / elapsed, 1) if last_time > 0 else self.target_ai_fps
                )
                self.last_ai_run[cam_id] = now
                return True
            return False

    def get_total_ai_fps(self) -> float:
        with self._lock:
            return round(sum(self.ai_fps_counters.values()), 1)


class APEXCameraWatchdog:
    """
    📡 چاودێری پچڕانی کامێراکان (Camera Heartbeat & Downtime Tracker)
    """

    def __init__(self):
        self.camera_states: dict = {}
        self._lock = threading.Lock()

    def report_frame_received(self, cam_id, cam_name: str = "") -> None:
        now = time.time()
        with self._lock:
            self.camera_states[cam_id] = {
                "name": cam_name or f"CAM-{cam_id}",
                "online": True,
                "last_seen": now,
                "disconnected_since": None,
            }

    def report_disconnected(self, cam_id, cam_name: str = "") -> None:
        now = time.time()
        with self._lock:
            state = self.camera_states.get(cam_id)
            if state is None or state["online"]:
                self.camera_states[cam_id] = {
                    "name": cam_name or f"CAM-{cam_id}",
                    "online": False,
                    "last_seen": state["last_seen"] if state else None,
                    "disconnected_since": now,
                }

    def get_attention_alerts(self) -> list:
        now = time.time()
        alerts = []
        with self._lock:
            for cam_id, info in self.camera_states.items():
                if not info["online"] and info["disconnected_since"]:
                    mins = int((now - info["disconnected_since"]) // 60)
                    alerts.append(
                        {
                            "level": "Needs attention",
                            "cam_id": cam_id,
                            "message": f"⚠️ {info['name']} ماوەی {mins} خولەکە پەیوەندیی پچڕاوە.",
                        }
                    )
        return alerts
    