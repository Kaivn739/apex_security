import streamlit as st
from database import init_db
from auth import require_auth
import dashboard
class sources:
    """Concrete video source used by the monitoring dashboard."""

    def __init__(self, source=0):
        self.source = source
        self._capture = None

    def open(self):
        if self._capture is None:
            import cv2
            self._capture = cv2.VideoCapture(self.source)
        return self.is_open()

    def read(self):
        if not self.open():
            return False, None
        return self._capture.read()

    def is_open(self):
        return self._capture is not None and self._capture.isOpened()

    def release(self):
        if self._capture is not None:
            self._capture.release()
            self._capture = None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.release()

# ڕێکخستنی شاشەی سەرەکیی پڕۆژە
st.set_page_config(
    page_title="Apex Security System",
    page_icon="🛡️",
    layout="wide"
)

def main():
    """Initialize the application and render the authenticated dashboard."""
    # دەستپێکردن و دروستکردنی داتا بەیس ئەگەر نەبێت
    init_db()
    
    # پشکنینی چوونەژوورەوە (ئەگەر نەیەتە ژوورەوە، تەنها فۆڕمی لۆگین دەبینێت)
    if require_auth():
        # نیشاندانی داشبۆردی چاودێری ئەگەر چووژوورەوە
        return dashboard.show_dashboard()

    return None

if __name__ == "__main__":
    main()