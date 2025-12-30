# vision/embryo_tracker.py

from math import hypot

# =========================
# EMBRYO INJECTION ZONE
# =========================

class EmbryoTracker:
    def __init__(self, merge_dist=40, match_dist=50):
        self.merge_dist = merge_dist
        self.match_dist = match_dist
        self.memory = {}
        self.next_id = 1

    def _merge(self, embryos):
        merged = []
        for e in embryos:
            cx, cy = e["cx"], e["cy"]
            label = e["label"]
            found = False

            for m in merged:
                if hypot(cx - m["cx"], cy - m["cy"]) < self.merge_dist:
                    m["cx"] = (m["cx"] + cx) // 2
                    m["cy"] = (m["cy"] + cy) // 2
                    found = True
                    break

            if not found:
                merged.append({"cx": cx, "cy": cy, "label": label})

        return merged

    def update(self, embryos):
        """
        embryos: list of dict {cx,cy,label}
        Returns:
            ids, centers, labels
        """

        merged = self._merge(embryos)
        updated = {}

        for e in merged:
            cx, cy, label = e["cx"], e["cy"], e["label"]
            assigned = False

            for eid, data in self.memory.items():
                ox, oy = data["pos"]
                if hypot(cx - ox, cy - oy) < self.match_dist:
                    updated[eid] = {"pos": (cx, cy), "label": label}
                    assigned = True
                    break

            if not assigned:
                updated[self.next_id] = {"pos": (cx, cy), "label": label}
                self.next_id += 1

        # garder les anciens
        for eid, data in self.memory.items():
            if eid not in updated:
                updated[eid] = data

        self.memory = updated

        ids = list(self.memory.keys())
        centers = [v["pos"] for v in self.memory.values()]
        labels = [v["label"] for v in self.memory.values()]

        return ids, centers, labels
