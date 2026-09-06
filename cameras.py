import cv2

class CameraStream:
    def __init__(self, source=0):
        """
        source دەکرێت ژمارەی 0 بێت بۆ دەستپێکردنی Webcam
        یان لینکی RTSP یان فایلی ڤیدیۆ بێت.
        """
        self.source = source
        self.cap = cv2.VideoCapture(self.source)

    def get_frame(self):
        if not self.cap.isOpened():
            return None
        
        ret, frame = self.cap.read()
        if not ret:
            # ئەگەر ڤیدیۆ بێت و تەواو بێت، لە سەرەتاوە دەستی پێدەکاتەوە (Loop)
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.cap.read()
            if not ret:
                return None
                
        return frame

    def release(self):
        if self.cap.isOpened():
            self.cap.release()