# utils/fps.py
import time


class FPSCounter:
    def __init__(self):
        self.last_time = time.time()
        self.frames = 0

    def update(self):
        self.frames += 1
        now = time.time()
        if now - self.last_time >= 1.0:
            fps = self.frames / (now - self.last_time)
            self.frames = 0
            self.last_time = now
            return fps
        return None
