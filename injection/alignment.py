# injection/alignment.py

from math import atan2, degrees


def is_aligned(center, needle, base_eps_deg=1.0, target_angle_deg=180.0, min_dx_px=12):
    """
    center: (cx,cy) embryo
    needle: (nx,ny) tip or align_point
    The embryo must be "in front" of the needle (to the left): dx < -min_dx_px
    and angle close to target (180° means horizontal left).
    """
    dx = center[0] - needle[0]
    dy = center[1] - needle[1]

    if dx >= -min_dx_px:
        return False

    ang = degrees(atan2(dy, dx))
    if ang < 0:
        ang += 360.0

    delta = min(abs(ang - target_angle_deg), 360.0 - abs(ang - target_angle_deg))

    # adaptive tolerance based on dy
    adaptive = max(3.5, min(12.0, base_eps_deg + abs(dy) / 50.0))
    return delta <= adaptive
