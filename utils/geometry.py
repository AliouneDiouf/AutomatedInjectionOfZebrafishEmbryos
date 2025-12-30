# utils/geometry.py
from math import atan2, degrees, hypot


def distance(p1, p2) -> float:
    return hypot(p1[0] - p2[0], p1[1] - p2[1])


def angle_deg(p1, p2) -> float:
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    ang = degrees(atan2(dy, dx))
    return ang + 360 if ang < 0 else ang
