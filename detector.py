import cv2
import numpy as np

# ناسینەوەی ڕەنگەکان بەپێی داواکارییەکەت (بە فۆرماتی BGR بۆ OpenCV)
# سەوز: 0% تا 45% (ئاسایی / بێ کێشە)
# پرتەقاڵی: 45% تا 75% (گومانلێکراو / لێکچوون)
# سوور: سەروو 75% (مەترسیدار / داواکراو)

COLOR_GREEN = (0, 255, 0)     # سەوز
COLOR_ORANGE = (0, 140, 255)  # پرتەقاڵی
COLOR_RED = (0, 0, 255)       # سوور

def evaluate_threat_level(similarity_score):
    """دیاریکردنی ڕەنگ و جۆری مەترسی بەپێی ڕێژەی سەدی لێکچوون"""
    if similarity_score < 45:
        return COLOR_GREEN, f"Normal ({similarity_score}%)"
    elif 45 <= similarity_score <= 75:
        return COLOR_ORANGE, f"Suspicious ({similarity_score}%)"
    else:
        return COLOR_RED, f"WANTED / HIGH RISK ({similarity_score}%)"

def process_frame_faces(frame):
    """
    لێرەدا پشکنینی دەموچاو ئەنجام دەدرێت و چوارچێوەکە بە ڕەنگی گونجاو دەکێشرێت.
    (وەک نموونە لێرەدا دەموچاوێک بە شێوەی ئۆتۆماتیک دەدۆزینەوە یان სიმوڵەیشن دەکەین)
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # بەکارهێنانی Haarcascade بۆ دۆزینەوەی سەرەتایی دەموچاو لە OpenCV دا
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
    
    for (x, y, w, h) in faces:
        # لێرەدا دەتوانیت ئەلگۆریزمی ناسینەوەی دەموچاو (Face Recognition) دابنێیت
        # بۆ نموونە نموونەیەک بە ڕێژەی لێکچوونی هەڕەمەکی یان بەراوردکاری ڕاستەقینە:
        # بۆ تاقیکردنەوە ڕێژەیەک دەستنیشان دەکەین (لە پرۆژەی راستەقینەدا لە داتابەیس دێت)
        sim_score = 65  # نموونە: 65% لێکچوون (کە دەبێتە پرتەقاڵی)
        
        box_color, label_text = evaluate_threat_level(sim_score)
        
        # کێشانی چوارچێوە لە دەوروبەری دەموچاوەکە بەو ڕەنگەی دیاری کراوە
        cv2.rectangle(frame, (x, y), (x+w, y+h), box_color, 2)
        
        # نوسینی دەق و ڕێژەی سەدی لەسەر چوارچێوەکە
        cv2.putText(frame, label_text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, box_color, 2
                    )
        
    return frame