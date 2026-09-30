import cv2
import tkinter as tk
from PIL import Image, ImageTk

cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)

if not cap.isOpened():
    print("❌ Capture Card نەکرایەوە")
    raise SystemExit

root = tk.Tk()
root.title("APEX DVR LIVE")
root.geometry("960x720")

label = tk.Label(root)
label.pack(fill="both", expand=True)

def update_frame():
    ret, frame = cap.read()

    if ret:
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(frame)
        image = image.resize((960, 720))
        photo = ImageTk.PhotoImage(image)

        label.configure(image=photo)
        label.image = photo

    root.after(30, update_frame)

def close():
    cap.release()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", close)
update_frame()
root.mainloop()
