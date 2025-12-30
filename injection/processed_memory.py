# injection/processed_memory.py

import time
from collections import deque
from math import hypot


class ProcessedMemory:
    def __init__(self, timeout_s: float, min_dist_px: float):
        self.timeout_s = timeout_s
        self.min_dist_px = min_dist_px
        self.items = deque(maxlen=200)  # (pt, ts)

    def _cleanup(self):
        now = time.time()
        while self.items and now - self.items[0][1] > self.timeout_s:
            self.items.popleft()

    def add(self, pt):
        self._cleanup()
        self.items.append((pt, time.time()))

    def contains(self, pt) -> bool:
        self._cleanup()
        for old_pt, _ in self.items:
            if hypot(pt[0] - old_pt[0], pt[1] - old_pt[1]) < self.min_dist_px:
                return True
        return False
