import cv2
import deepface
def start_camera(db_path="suspects"):
    cap = cv2.VideoCapture(0)
    frame_count = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1
        
        # پشکنین لەسەر هەر 30 فریمێک جارێک بۆ خێرایی سیستەمەکە
        if frame_count % 30 == 0:
            try:
                dfs = deepface.DeepFace.find(img_path=frame, db_path=db_path, enforce_detection=False)
                if len(dfs) > 0 and not dfs[0].empty:
                    identity = dfs[0]['identity'].iloc[0]
                    print(f"گۆمانلێکراو دۆزرایەوە: {identity}")
            except Exception as e:
                pass

        # نیشاندانى پەنجەرەی کامێرا
        cv2.imshow("APEX - Surveillance System", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()