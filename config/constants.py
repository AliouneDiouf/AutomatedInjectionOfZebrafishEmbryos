# config/constants.py

# --- Alignment & geometry ---
EPSILON_DEG = 1.0
DISTANCE_MIN_BASE = 80
MEMORY_TIMEOUT = 2.0
MOVE_INTERVAL = 0.4

# --- Contact detection ---
PATCH_RADIUS = 32
IMG_CLF_SIZE = 64
CONF_CONTACT = 0.99
CLASS_NAMES = ["contact", "non_contact"]

# --- Injection logic ---
TARGET_DURATION = 2
SPEED_FACTOR = 1
SMOOTHING_WINDOW = 21
POLY_ORDER = 3

# --- Mechanical conversion ---
GEAR_RATIO = 27 / 20
LEAD_PITCH_MM = 0.25
STEPS_PER_REV = 200
STEP_TO_MM = LEAD_PITCH_MM / STEPS_PER_REV

# --- Labels ---
YOLK_LABELS = {"CytoLivable", "YolkLivable"}
DEAD_LABELS = {"Dead"}
