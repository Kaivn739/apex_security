import cv2
import requests
import time

# 📍 زانیارییەکانی تێلیگرام بۆتی APEX
TELEGRAM_BOT_TOKEN = "8858143126:AAEjeU3OvWin4TfLMnRjbKmFQ8KacG9bNz8"
TELEGRAM_CHAT_ID = "1060262873"

# فەرهەنگی ڕاگرتنی کات بۆ ڕێگری لە ناردنی دووبارە (Anti-Spam Cooldown)
last_alert_time = {}
COOLDOWN_SECONDS = 30  # دوای ٣٠ چركە جارێکی تر ئاگاداری بۆ هەمان تارگێت دەنێرێتەوە


def send_target_telegram_alert(target_name: str, camera_name: str, frame):
    """ناردنی وێنە و زانیاریی تارگێتی دەستنیشانکراو بۆ تێلیگرام"""
    global last_alert_time
    current_time = time.time()

    # ڕێگری لە دووبارە ناردنەوە لە ماوەی کۆڵداوندا
    if target_name in last_alert_time:
        if current_time - last_alert_time[target_name] < COOLDOWN_SECONDS:
            return

    last_alert_time[target_name] = current_time

    # دەقی پەیامی ئاگادارکردنەوە
    caption_text = (
        f"🚨 APEX TARGET DETECTED!\n\n"
        f"👤 Target Name: {target_name}\n"
        f"📹 Camera: {camera_name}\n"
        f"⏰ Time: {time.strftime('%Y-%m-%d %H:%M:%S')}"
    )

    # گۆڕینی فریمی OpenCV بۆ بایتی وێنەی JPG
    ret, buffer = cv2.imencode(".jpg", frame)
    if not ret:
        return

    img_bytes = buffer.tobytes()

    # ناردنی وێنە و زانیاری ڕاستەوخۆ بۆ چاتی تێلیگرامەکەت
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "caption": caption_text,
        "parse_mode": "Markdown",
    }
    files = {"photo": ("target.jpg", img_bytes, "image/jpeg")}

    try:
        requests.post(url, data=payload, files=files, timeout=5)
    except Exception as e:
        print(f"Error sending Telegram alert: {e}")
