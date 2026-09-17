import cv2
import os
import threading
import time
from typing import Union

class CameraStream:
    def __init__(self, source: Union[int, str] = 0):
        self.source = source
        if isinstance(self.source, str) and self.source.isdigit():
            self.source = int(self.source)

        self.cap = None
        self.latest_frame = None
        self.running = True

        self._init_camera()

        # چالاککردنی تات-دەست (Thread) بۆ خوێندنەوەی ئۆتۆماتیکیی فریمەکان
        self.thread = threading.Thread(target=self._update_loop, daemon=True)
        self.thread.start()

    def _init_camera(self):
        try:
            if isinstance(self.source, str) and self.source.lower().startswith("rtsp"):
                os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
                    "rtsp_transport;udp|fflags;nobuffer|flags;low_delay"
                )
                self.cap = cv2.VideoCapture(self.source, cv2.CAP_FFMPEG)
            elif isinstance(self.source, int):
                self.cap = cv2.VideoCapture(self.source, cv2.CAP_DSHOW)
                if not self.cap.isOpened():
                    self.cap = cv2.VideoCapture(self.source)
            else:
                self.cap = cv2.VideoCapture(str(self.source))

            if self.cap and self.cap.isOpened():
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception as e:
            print(f"Error initializing camera: {e}")

    def _update_loop(self):
        while self.running:
            if self.cap and self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret and frame is not None:
                    self.latest_frame = frame
                else:
                    time.sleep(0.01)
            else:
                time.sleep(0.1)

    def get_frame(self):
        return self.latest_frame

    def release(self):
        self.running = False
        if self.cap and self.cap.isOpened():
            self.cap.release()
            self.cap = None
