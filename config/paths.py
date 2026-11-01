# config/paths.py
"""Filesystem locations. Every path can be overridden with an environment
variable, so the project runs on any machine without editing the source."""

import os
from pathlib import Path

# Project root (this file lives in <root>/config/)
BASE_DIR = Path(__file__).resolve().parents[1]

# Trained weights. Default: <root>/models/
MODELS_DIR = Path(os.environ.get("ZINJ_MODELS_DIR", BASE_DIR / "models"))
MODEL_PATH = Path(os.environ.get("ZINJ_MODEL_DETECT", MODELS_DIR / "tip_embryo_seg.pt"))
MODEL_CLASSIFY = Path(os.environ.get("ZINJ_MODEL_CONTACT", MODELS_DIR / "contact_classifier.pt"))

# Recorded operator injection profile
PROFILE_CSV_PATH = Path(
    os.environ.get("ZINJ_PROFILE_CSV", BASE_DIR / "profiles" / "injection_profile.csv")
)

# Where injection videos are written
VIDEO_DIR = Path(os.environ.get("ZINJ_VIDEO_DIR", BASE_DIR / "recordings"))
VIDEO_DIR.mkdir(parents=True, exist_ok=True)
