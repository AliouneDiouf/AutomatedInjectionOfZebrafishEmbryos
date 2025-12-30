# vision/tip_tracker.py

import numpy as np
from collections import deque
import cv2


class TipTracker:
    def __init__(self, history_size=5, max_lost=4):
        self.history = deque(maxlen=history_size)
        self.filtered_tip = None
        self.lost_frames = 0
        self.max_lost = max_lost

    def _largest_component(self, mask_u8):
        """
        Garde uniquement la plus grande composante connexe du masque
        (supprime bruit et pixels parasites).
        """
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
            mask_u8, connectivity=8
        )

        if num_labels <= 1:
            return mask_u8

        # stats[0] = background
        largest_label = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
        clean = np.zeros_like(mask_u8)
        clean[labels == largest_label] = 1
        return clean

    def update(self, pipettes, frame_w, frame_h):
        """
        Args:
            pipettes: list of dict (from YoloDetector)
            frame_w, frame_h: dimensions du frame courant

        Returns:
            (x, y) tip filtré ou None
        """

        # -------------------------
        # AUCUNE DÉTECTION
        # -------------------------
        if not pipettes:
            self.lost_frames += 1
            if self.lost_frames < self.max_lost and self.filtered_tip is not None:
                return self.filtered_tip
            self.filtered_tip = None
            return None

        # -------------------------
        # SÉLECTION DE LA PIPETTE
        # -------------------------
        pipettes.sort(
            key=lambda p: (p.get("x2", 0), p.get("conf", 0.0)),
            reverse=True
        )
        best = pipettes[0]

        raw_tip = None
        mask = best.get("mask", None)

        # -------------------------
        # CAS SEGMENTATION (PRIORITAIRE)
        # -------------------------
        if mask is not None:
            # masque binaire
            mask_u8 = (mask > 0).astype(np.uint8)

            # 🔥 CRITIQUE : resize masque YOLO → taille image réelle
            mask_u8 = cv2.resize(
                mask_u8,
                (frame_w, frame_h),
                interpolation=cv2.INTER_NEAREST
            )

            # 🔥 nettoyage du masque
            mask_u8 = self._largest_component(mask_u8)

            ys, xs = np.where(mask_u8 > 0)

            if len(xs) > 40:
                pts = np.column_stack((xs, ys)).astype(np.float32)

                # -------------------------
                # PCA : axe principal
                # -------------------------
                mean = pts.mean(axis=0)
                centered = pts - mean
                cov = np.cov(centered, rowvar=False)
                eigvals, eigvecs = np.linalg.eigh(cov)
                direction = eigvecs[:, np.argmax(eigvals)]

                # forcer l'orientation vers la gauche (tip côté gauche)
                if direction[0] > 0:
                    direction = -direction

                # projection sur l'axe
                proj = centered @ direction
                idx = int(np.argmax(proj))

                tip_x, tip_y = pts[idx]
                raw_tip = (int(tip_x), int(tip_y))

        # -------------------------
        # FALLBACK : BOX CENTER
        # -------------------------
        if raw_tip is None:
            raw_tip = (
                int(best.get("cx", 0)),
                int(best.get("cy", 0))
            )

        # -------------------------
        # FILTRAGE TEMPOREL
        # -------------------------
        self.history.append(raw_tip)
        self.lost_frames = 0

        xs_hist = [p[0] for p in self.history]
        ys_hist = [p[1] for p in self.history]

        self.filtered_tip = (
            int(np.mean(xs_hist)),
            int(np.mean(ys_hist))
        )

        return self.filtered_tip
