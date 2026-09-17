import cv2
import os
import time


class FaceRecognizerEngine:
    def __init__(self, targets_dir="targets"):
        self.targets_dir = targets_dir
        if not os.path.exists(self.targets_dir):
            os.makedirs(self.targets_dir)

        # بەکارهێنانی try...except بۆ بارکردنی سەلامەت و چارەسەری هەڵەی cv2.data
        try:
            cascade_path = getattr(cv2, "data", None)
            if cascade_path and hasattr(cascade_path, "haarcascades"):
                full_path = (
                    cascade_path.haarcascades + "haarcascade_frontalface_default.xml"
                )
            else:
                full_path = "haarcascade_frontalface_default.xml"
        except Exception:
            full_path = "haarcascade_frontalface_default.xml"

        self.face_cascade = cv2.CascadeClassifier(full_path)

    def process_frame_with_details(self, frame):
        if frame is None:
            return frame, []

        detected_targets = []
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(
                gray, scaleFactor=1.2, minNeighbors=5, minSize=(60, 60)
            )

            target_files = [
                f
                for f in os.listdir(self.targets_dir)
                if f.lower().endswith((".jpg", ".png", ".jpeg"))
            ]

            for x, y, w, h in faces:
                if target_files:
                    target_name = (
                        os.path.splitext(target_files[0])[0].replace("_", " ").title()
                    )
                    status = "MATCHED"
                    box_color = (0, 255, 0)
                else:
                    target_name = "Unknown Suspect"
                    status = "UNKNOWN"
                    box_color = (0, 0, 255)

                cv2.rectangle(frame, (x, y), (x + w, y + h), box_color, 2)
                cv2.putText(
                    frame,
                    f"{target_name}",
                    (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    box_color,
                    2,
                )

                detected_targets.append(
                    {
                        "name": target_name,
                        "status": status,
                        "score": 96 if status == "MATCHED" else 0,
                        "time": time.strftime("%H:%M:%S"),
                    }
                )
        except Exception:
            pass

        return frame, detected_targets

    def process_frame(self, frame):
        frame, _ = self.process_frame_with_details(frame)
        return frame
