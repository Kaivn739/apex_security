import cv2
import easyocr
import re
import time


class ALPREngine:
    def __init__(self):
        # دیاریکردنی زمانی ئینگلیزی بۆ خوێندنەوەی ژمارەی تابلۆکان
        self.reader = easyocr.Reader(["en"], gpu=False)

    def process_frame(self, frame):
        if frame is None:
            return frame, []

        detected_plates = []
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # خوێندنەوەی دەق لەسەر وێنەکە
        results = self.reader.readtext(gray)

        for bbox, text, prob in results:
            # پاڵاوتنی دەقەکە (تەنها پیت و ژمارەی تابلۆ)
            clean_text = re.sub(r"[^A-Za-z0-9]", "", text).upper()

            # زۆرکردنی گۆڕینی prob بۆ float بۆ ڕێگری لە هەڵەی Pylance
            try:
                prob_val = float(prob)
            except (ValueError, TypeError):
                prob_val = 0.0

            # دەستنیشانکردنی ئەوانەی ڕێژەی دڵنیایییان لە %40 زیاترە
            if prob_val > 0.4 and len(clean_text) >= 4:
                tl, _, br, _ = bbox
                top_left = (int(tl[0]), int(tl[1]))
                bottom_right = (int(br[0]), int(br[1]))

                # کێشانی چوارچێوە لە دەوری تابلۆکە
                cv2.rectangle(frame, top_left, bottom_right, (255, 165, 0), 2)
                cv2.putText(
                    frame,
                    f"PLATE: {clean_text}",
                    (top_left[0], top_left[1] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 165, 0),
                    2,
                )

                detected_plates.append(
                    {
                        "plate": clean_text,
                        "confidence": int(prob_val * 100),
                        "time": time.strftime("%H:%M:%S"),
                    }
                )

        return frame, detected_plates
