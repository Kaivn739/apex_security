import cv2
import os
from typing import Union


class CameraStream:
    def __init__(self, source: Union[int, str] = 0):
        self.source = source
        self.cap = None
        self._init_camera()

    def _init_camera(self):
        """دەستپێکردن و کردنەوەی سەلامەتی کامێرا بەبێ پچڕان"""
        # ئەگەر کامێرای IP / RTSP بێت (دەق/String)
        if isinstance(self.source, str):
            if self.source.startswith("rtsp"):
                os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;udp"
                self.cap = cv2.VideoCapture(self.source, cv2.CAP_FFMPEG)
            else:
                self.cap = cv2.VideoCapture(self.source)
        else:
            # بۆ وێبکامی لۆکاڵ (Index 0 یان 1)
            try:
                src_idx = int(self.source)
                self.cap = cv2.VideoCapture(src_idx, cv2.CAP_DSHOW)
                if not self.cap or not self.cap.isOpened():
                    self.cap = cv2.VideoCapture(src_idx)
            except (ValueError, TypeError):
                self.cap = cv2.VideoCapture(self.source)

        if self.cap and self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    def get_frame(self):
        """وەرگرتنی فریمەکان بە پارێزراوی"""
        if self.cap is None or not self.cap.isOpened():
            self._init_camera()

        if self.cap is None or not self.cap.isOpened():
            return None

        ret, frame = self.cap.read()
        if not ret or frame is None:
            return None

        return frame

    def release(self):
        """داخستنی کامێرا و ئازادکردنی ڕام"""
        if self.cap and self.cap.isOpened():
            self.cap.release()
            self.cap = None
