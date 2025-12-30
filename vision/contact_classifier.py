# vision/contact_classifier.py

import cv2
from ultralytics import YOLO
from config.constants import PATCH_RADIUS, IMG_CLF_SIZE, CONF_CONTACT, CLASS_NAMES


class ContactClassifier:
    def __init__(self, model_path):
        self.model = YOLO(model_path)

    def classify(self, gray_frame, tip, frame_w, frame_h):
        """
        Returns: (contact_detected: bool, score: float, patch_rgb)
        """
        tx, ty = tip

        x1 = max(0, tx - PATCH_RADIUS)
        x2 = min(frame_w, tx + PATCH_RADIUS)
        y1 = max(0, ty - PATCH_RADIUS)
        y2 = min(frame_h, ty + PATCH_RADIUS)

        patch = gray_frame[y1:y2, x1:x2]
        if patch.shape[0] < 16 or patch.shape[1] < 16:
            return False, 0.0, None

        patch_resized = cv2.resize(patch, (IMG_CLF_SIZE, IMG_CLF_SIZE))
        patch_rgb = cv2.cvtColor(patch_resized, cv2.COLOR_GRAY2RGB)

        res = self.model.predict(
            patch_rgb,
            imgsz=IMG_CLF_SIZE,
            verbose=False
        )[0]

        idx = int(res.probs.top1)
        score = float(res.probs.top1conf)
        cls = CLASS_NAMES[idx]

        contact = (cls == "contact" and score >= CONF_CONTACT)
        print(
    f"TIP={tip} | PATCH={patch.shape} | "
    f"CLASS={cls if 'cls' in locals() else None} | "
    f"SCORE={score if 'score' in locals() else None}"
)

        return contact, score, patch_rgb
