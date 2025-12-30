# utils/video_recorder.py
import cv2
import datetime
from config.paths import VIDEO_DIR


class VideoRecorder:
    def __init__(self):
        self.writer = None

    def start(self, frame_shape):
        h, w = frame_shape[:2]
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = VIDEO_DIR / f"injection_{ts}.mp4"

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        self.writer = cv2.VideoWriter(str(path), fourcc, 20.0, (w, h))
        print(f"🎥 Recording video: {path}")

    def write(self, frame):
        if self.writer is not None:
            self.writer.write(frame)

    def stop(self):
        if self.writer is not None:
            self.writer.release()
            self.writer = None
            print("🎥 Video saved.")
