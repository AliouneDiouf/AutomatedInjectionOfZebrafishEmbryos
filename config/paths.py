# config/paths.py
from pathlib import Path

# Racine projet (zebrafish_injection)
BASE_DIR = Path(__file__).resolve().parents[1]

MODEL_PATH = Path(r"C:\Users\anima\Desktop\ALIOUNE\postdoc\MODELS\newmodeltip1.pt")
MODEL_CLASSIFY = Path(r"C:\Users\anima\Desktop\ALIOUNE\postdoc\MODELS\best_contact_model1.pt")

PROFILE_CSV_PATH = Path(
    r"C:\Users\anima\Desktop\ALIOUNE\postdoc\codes_good\ProfilsInjKarim\InjInj3_20251107_124549.csv"
)

VIDEO_DIR = Path(r"C:\Users\anima\Desktop\ALIOUNE\postdoc\Injection_videos")
VIDEO_DIR.mkdir(parents=True, exist_ok=True)
