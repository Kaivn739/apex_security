print("APEX DVR TEST STARTED")

import cv2
import tkinter as tk

cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)

print("Capture opened:", cap.isOpened())

ret, frame = cap.read()
print("Frame received:", ret)

if ret:
    print("Frame size:", frame.shape)

root = tk.Tk()
root.title("APEX DVR TEST")
root.geometry("1000x600")

label = tk.Label(root, text="APEX DVR TEST", font=("Arial", 30))
label.pack(expand=True)

print("Window starting...")

root.mainloop()

cap.release()
