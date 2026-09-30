import cv2


class APEXFaceRecognizer:
    def __init__(self):
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self.face_cascade = cv2.CascadeClassifier(cascade_path)

    def detect_and_draw(self, frame, enabled=True):
        if not enabled or frame is None or self.face_cascade.empty():
            return frame, []

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray, scaleFactor=1.2, minNeighbors=4, minSize=(30, 30)
        )

        detected_faces = []
        for x, y, w, h in faces:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.rectangle(frame, (x, y - 25), (x + 140, y), (15, 23, 42), -1)
            cv2.putText(
                frame,
                "FACE DETECTED",
                (x + 5, y - 7),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (0, 255, 0),
                1,
            )

            detected_faces.append({"box": (x, y, w, h), "status": "VERIFIED"})

        return frame, detected_faces