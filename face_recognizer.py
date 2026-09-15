import cv2
import os
import numpy as np
from datetime import datetime

class FaceRecognizerEngine:
    def __init__(self, targets_dir="targets"):
        self.targets_dir = targets_dir
        self.known_faces = []
        self.known_names = []
        
        # بارکردنی مۆدێلی ڕووخسار
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        
        self.load_targets()

    def load_targets(self):
        """خوێندنەوەی وێنەکانی ناو فۆڵدەری targets"""
        if not os.path.exists(self.targets_dir):
            os.makedirs(self.targets_dir)
            return

        for file_name in os.listdir(self.targets_dir):
            if file_name.lower().endswith(('.jpg', '.jpeg', '.png')):
                name = os.path.splitext(file_name)[0]
                img_path = os.path.join(self.targets_dir, file_name)
                img = cv2.imread(img_path)
                
                if img is not None:
                    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    faces = self.face_cascade.detectMultiScale(gray, 1.1, 5)
                    for (x, y, w, h) in faces:
                        face_roi = cv2.resize(gray[y:y+h, x:x+w], (100, 100))
                        self.known_faces.append(face_roi)
                        self.known_names.append(name)
                        break

    def process_frame(self, frame):
        if frame is None:
            return frame

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(40, 40))

        for (x, y, w, h) in faces:
            current_face = cv2.resize(gray[y:y+h, x:x+w], (100, 100))
            matched_name = "Unknown Suspect"
            color = (0, 0, 255)  # ڕەنگی سوور

            for idx, known_face in enumerate(self.known_faces):
                diff = cv2.absdiff(current_face, known_face)
                score = np.mean(diff)

                if score < 55:  
                    matched_name = f"TARGET: {self.known_names[idx]}"
                    color = (0, 255, 0)  # ڕەنگی کەسک
                    break

            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            cv2.rectangle(frame, (x, y - 25), (x + w, y), color, cv2.FILLED)
            cv2.putText(frame, matched_name, (x + 5, y - 7),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        return frame

    def process_frame_with_details(self, frame):
        if frame is None:
            return frame, []

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(40, 40))
        detected_targets = []

        for (x, y, w, h) in faces:
            current_face = cv2.resize(gray[y:y+h, x:x+w], (100, 100))
            matched_name = "Unknown Suspect"
            status = "UNKNOWN"
            confidence_score = 0
            color = (0, 0, 255) # سوور

            for idx, known_face in enumerate(self.known_faces):
                diff = cv2.absdiff(current_face, known_face)
                score = np.mean(diff)

                if score < 55:  
                    matched_name = self.known_names[idx]
                    status = "MATCHED"
                    confidence_score = round(100 - score, 1)
                    color = (0, 255, 0) # کەسک
                    break

            # وێنەکێشان لەسەر وێنەکە
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            cv2.putText(frame, matched_name, (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

            # پاشەکەوتکردنی زانیاری بۆ بۆکسەکەی دەستەڕاست
            detected_targets.append({
                "name": matched_name,
                "status": status,
                "score": confidence_score,
                "time": datetime.now().strftime("%H:%M:%S")
            })

        return frame, detected_targets