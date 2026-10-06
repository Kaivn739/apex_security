import cv2
import tkinter as tk
from PIL import Image, ImageTk

print("APEX DVR LIVE STARTED")

# ==============================
# Capture Card
# ==============================

cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)

if not cap.isOpened():
    print("❌ Capture Card نەکرایەوە")
    raise SystemExit

# Performance settings
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
cap.set(cv2.CAP_PROP_FPS, 30)

print(
    "Resolution:",
    int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
    "x",
    int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
)

print("FPS setting:", cap.get(cv2.CAP_PROP_FPS))

# ==============================
# APEX Window
# ==============================

root = tk.Tk()
root.title("APEX - DVR LIVE")
root.geometry("960x720")
root.minsize(640, 480)

label = tk.Label(root, bg="black")
label.pack(fill="both", expand=True)

# Keep a reference to the current image
current_photo = None


# ==============================
# Live Frame Update
# ==============================


def update_frame():
    global current_photo

    ret, frame = cap.read()

    if ret:
        # OpenCV BGR → RGB
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Convert to PIL
        image = Image.fromarray(frame)

        # Display size
        image = image.resize((960, 720), Image.Resampling.LANCZOS)

        # Convert for Tkinter
        current_photo = ImageTk.PhotoImage(image)

        # Show frame
        label.configure(image=current_photo)

    else:
        label.configure(text="❌ No video signal", image="")

    # ~30 FPS update loop
    root.after(33, update_frame)


# ==============================
# Close
# ==============================


def close_app():
    print("APEX DVR LIVE CLOSING...")

    cap.release()
    root.destroy()


root.protocol("WM_DELETE_WINDOW", close_app)

# Start live video
update_frame()

# Start GUI
root.mainloop()
