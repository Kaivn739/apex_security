import cv2
import numpy as np
import requests
from apex_brain import APEXBrainCore


class APEXALPRPipeline:
    def __init__(self, telegram_token="", chat_id=""):
        self.brain = APEXBrainCore()

        self.target_database = {
            "22B-10922": {
                "status": "SUSPECT",
                "owner": "ئیسماعیل زاهیر",
                "severity": "HIGH",
            },
            "89C-04048": {
                "status": "BLACK_LISTED",
                "owner": "مەترسیدار / نەناسراو",
                "severity": "CRITICAL",
            },
            "33V-P377": {
                "status": "AUTHORIZED",
                "owner": "ئۆتۆمبێلی ڕێگەپێدراو",
                "severity": "LOW",
            },
        }
        self.telegram_token = telegram_token
        self.chat_id = chat_id
        self.alerted_plates = set()

    def send_telegram_alert(self, plate_number, info):
        if not self.telegram_token or not self.chat_id:
            return

        message = (
            f"🚨 **APEX EMERGENCY SECURITY ALERT** 🚨nn"
            f"🚘 **تابلۆی دۆزراوە:** `{plate_number}`n"
            f"👤 **خاوەن / زانیاری:** {info['owner']}n"
            f"🏷️ **دۆخی ئەمنی:** {info['status']}n"
            f"⚠️ **ئاستی مەترسی:** {info['severity']}n"
            f"📍 **شوێن:** Erbil Security Zone - CAM-01"
        )
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        try:
            requests.post(
                url,
                data={
                    "chat_id": self.chat_id,
                    "text": message,
                    "parse_mode": "Markdown",
                },
                timeout=2,
            )
        except Exception:
            pass

    def generate_dynamic_plate(self, track_id):
        known_list = [
            "18A-40291",
            "22B-10922",
            "12M-90211",
            "33V-P377",
            "89C-04048",
            "11A-30492",
        ]
        idx = track_id % len(known_list)
        return known_list[idx]

    def evaluate_plate(self, plate_number):
        if plate_number in self.target_database:
            info = self.target_database[plate_number]
            if (
                info["status"] in ["SUSPECT", "BLACK_LISTED"]
                and plate_number not in self.alerted_plates
            ):
                # 🧠 1. ڕەوانەکردن بۆ عەقڵی APEX بۆ پاشەکەوتکردن لە داتابەیسدا
                self.brain.log_alert(plate_number, info["owner"], info["status"])

                # 📲 2. ناردنی ئاگاداری بۆ تەلەگرام
                self.send_telegram_alert(plate_number, info)
                self.alerted_plates.add(plate_number)
            return info
        return {
            "status": "AUTHORIZED",
            "owner": "عادی / ڕێگەپێدراو",
            "severity": "NONE",
        }