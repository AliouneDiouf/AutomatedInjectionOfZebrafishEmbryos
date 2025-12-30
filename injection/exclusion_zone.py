# injection/exclusion_zone.py

from math import hypot


class ExclusionZone:
    def __init__(self, radius_px: int):
        self.radius = radius_px
        self.active = False
        self.last_injected = None  # (x,y)

    def enable(self, pt):
        self.last_injected = pt
        self.active = True

    def disable(self):
        self.active = False

    def contains(self, pt):
        if not self.active or self.last_injected is None:
            return False
        return hypot(pt[0] - self.last_injected[0], pt[1] - self.last_injected[1]) < self.radius
