import numpy as np
from ultralytics import YOLO
from config.constants import YOLK_LABELS, DEAD_LABELS


class YoloDetector:
    def __init__(self, model_path, device="cpu", conf=0.265, imgsz=640):
        self.model = YOLO(model_path)
        self.device = device
        self.conf = conf
        self.imgsz = imgsz

    def detect(self, frame):
        """
        Returns:
            pipettes: list of dict {
                cx, cy, x1,y1,x2,y2, conf, mask (GLOBAL)
            }
            embryos: list of dict {
                cx, cy, label
            }
        """

        results = self.model.predict(
            source=frame,
            imgsz=self.imgsz,
            conf=self.conf,
            device=self.device,
            verbose=False
        )

        r = results[0]
        boxes = r.boxes
        masks = r.masks.data.cpu().numpy() if r.masks is not None else None

        pipettes = []
        embryos = []

        if boxes is None:
            return pipettes, embryos

        for i, b in enumerate(boxes):
            cls_id = int(b.cls[0])
            label = self.model.names[cls_id]
            conf = float(b.conf[0])

            x1, y1, x2, y2 = map(int, b.xyxy[0])
            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2

            # -------------------------
            # PIPETTE
            # -------------------------
            if label == "Pipette":
                det = {
                    "cx": cx,
                    "cy": cy,
                    "x1": x1, "y1": y1,
                    "x2": x2, "y2": y2,
                    "conf": conf
                }

                # 🔥 MASQUE GLOBAL (H, W)
                if masks is not None:
                    det["mask"] = masks[i].astype(np.uint8)

                pipettes.append(det)
                continue

            # -------------------------
            # EMBRYONS
            # -------------------------
            if label in YOLK_LABELS or label in DEAD_LABELS:
                embryos.append({
                    "cx": cx,
                    "cy": cy,
                    "label": label
                })

        return pipettes, embryos
