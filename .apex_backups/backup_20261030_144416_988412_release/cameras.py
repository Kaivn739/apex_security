import os
import cv2
import threading
import numpy as np
import time


class CameraStreamer:
    def __init__(self, cam_id, source, cam_type):
        self.cam_id = cam_id
        self.source = source
        self.cam_type = cam_type
        self.running = True
        self.lock = threading.Lock()
        self.frame = np.zeros((480, 640, 3), dtype=np.uint8)

        cv2_data = getattr(cv2, "data", None)
        if cv2_data is not None and hasattr(cv2_data, "haarcascades"):
            cascade_dir = os.path.join(cv2_data.haarcascades)
        else:
            cascade_dir = os.path.join(os.path.dirname(cv2.__file__), "data", "haarcascades")

        cascade_path = os.path.join(cascade_dir, "haarcascade_frontalface_default.xml")
        self.face_cascade = cv2.CascadeClassifier(cascade_path)

        self.enable_face_id = True
        self.enable_alpr = True

        self.thread = threading.Thread(target=self._update, daemon=True)
        self.thread.start()

    def _update(self):
        while self.running:
            if str(self.source) == "0" or "Webcam" in str(self.cam_type):
                cap_source = 0
            else:
                cap_source = self.source

            cap = cv2.VideoCapture(cap_source)

            while self.running and cap.isOpened():
                ret, frame = cap.read()

                if not ret:
                    time.sleep(0.01)
                    break

                if frame is not None and frame.size > 0:
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    with self.lock:
                        self.frame = rgb_frame

                time.sleep(0.03)

            cap.release()
            time.sleep(0.2)

    def get_frame(self):
        with self.lock:
            return self.frame.copy()

    def update_source(self, new_source, new_type):
        if self.source != new_source or self.cam_type != new_type:
            self.source = new_source
            self.cam_type = new_type

    def stop(self):
        self.running = False


class APEXCameraManager:
    def __init__(self, retention_days=90):
        self.retention_days = retention_days
        self.streamers = {}
        self.ai_modes = {}

    def get_streamer(self, cam_id, source, cam_type):
        if cam_id not in self.streamers:
            self.streamers[cam_id] = CameraStreamer(cam_id, source, cam_type)
        else:
            self.streamers[cam_id].update_source(source, cam_type)
        return self.streamers[cam_id]

    def set_camera_ai_mode(self, cam_id, face_id=True, alpr=True):
        self.ai_modes[cam_id] = {"face_id": face_id, "alpr": alpr}
        if cam_id in self.streamers:
            self.streamers[cam_id].enable_face_id = face_id
            self.streamers[cam_id].enable_alpr = alpr