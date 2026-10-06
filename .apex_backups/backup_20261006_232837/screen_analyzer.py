import cv2
import numpy as np
from PIL import ImageGrab
from typing import Optional


class ScreenAnalyzer:
    def __init__(self, bbox: Optional[tuple] = None):
        """
        bbox: (left, top, right, bottom)
        ئەگەر None بێت تەواوی شاشەکە دەگرێت، یان بەشێکی تایبەت لە شاشەی کامێراکان.
        """
        self.bbox = bbox

    def get_screen_frame(self) -> Optional[np.ndarray]:
        """گرتنی وێنەی شاشەکە بەبێ دروستکردنی فشاری کامێرا"""
        try:
            # گرتنی فریمی شاشە
            screen = ImageGrab.grab(bbox=self.bbox)
            frame = np.array(screen)
            # گۆڕینی ڕەنگ لە RGB بۆ BGR بۆ OpenCV
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            return frame_bgr
        except Exception as e:
            print(f"Error capturing screen: {e}")
            return None