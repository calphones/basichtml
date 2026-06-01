"""Staircase detection, classification, and 3D parameter extraction."""

from __future__ import annotations
from dataclasses import dataclass
import math
import numpy as np
from typing import Optional

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

from ..types import Vec2, StaircaseElement


@dataclass
class StairClassification:
    element: StaircaseElement
    confidence: float
    has_landing: bool
    open_riser: bool
    direction: str  # "up", "down", "unknown"
    stair_type: str  # "straight", "L-shaped", "U-shaped", "spiral"


class StaircaseDetector:
    """Detect and classify staircases in floor plan images.

    Floor plan representation of stairs:
    - Straight run: parallel horizontal lines with equal spacing (treads)
    - Landing: break in parallel pattern with a perpendicular section
    - Direction arrow: diagonal line or arrow indicating up/down
    - Open-to-below: usually annotated "OPEN TO BELOW" or similar
    """

    TREAD_SPACING_RANGE_PX = (6, 30)
    MIN_TREADS = 4
    MAX_TREADS = 20
    DIRECTION_ARROW_ANGLE_RANGE = (30, 60)  # degrees from horizontal

    def __init__(self, scale_m_per_px: float = 1.0):
        if not HAS_CV2:
            raise ImportError("opencv-python is required")
        self.scale_m_per_px = scale_m_per_px

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect_and_classify(self, image: np.ndarray) -> list[StairClassification]:
        binary = self._to_binary(image)
        candidates = self._find_stair_regions(binary)
        results = []
        for bbox, region in candidates:
            classification = self._classify_region(region, bbox)
            if classification is not None:
                results.append(classification)
        return results

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------

    def _to_binary(self, image: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY) if len(image.shape) == 3 else image
        _, binary = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY_INV)
        return binary

    def _find_stair_regions(self, binary: np.ndarray):
        """Find rectangular regions containing parallel horizontal lines (treads)."""
        h, w = binary.shape
        lines = cv2.HoughLinesP(binary, 1, np.pi / 180, threshold=20,
                                 minLineLength=30, maxLineGap=4)
        if lines is None:
            return []

        # Group nearly-horizontal lines
        h_lines = [(l[0][0], l[0][1], l[0][2], l[0][3])
                   for l in lines if abs(l[0][3] - l[0][1]) < 4]
        if len(h_lines) < self.MIN_TREADS:
            return []

        h_lines.sort(key=lambda l: l[1])
        # Find groups of evenly-spaced horizontal lines
        groups = self._group_evenly_spaced(h_lines)
        candidates = []
        for group in groups:
            if len(group) < self.MIN_TREADS:
                continue
            x_min = min(l[0] for l in group)
            x_max = max(l[2] for l in group)
            y_min = min(l[1] for l in group)
            y_max = max(l[3] for l in group)
            bbox = (x_min, y_min, x_max - x_min, y_max - y_min)
            region = binary[y_min:y_max+1, x_min:x_max+1]
            candidates.append((bbox, region))
        return candidates

    def _group_evenly_spaced(self, h_lines: list[tuple]) -> list[list[tuple]]:
        groups: list[list[tuple]] = []
        if not h_lines:
            return groups
        current_group = [h_lines[0]]
        for i in range(1, len(h_lines)):
            gap = h_lines[i][1] - h_lines[i-1][1]
            lo, hi = self.TREAD_SPACING_RANGE_PX
            if lo <= gap <= hi:
                current_group.append(h_lines[i])
            else:
                if len(current_group) >= self.MIN_TREADS:
                    groups.append(current_group)
                current_group = [h_lines[i]]
        if len(current_group) >= self.MIN_TREADS:
            groups.append(current_group)
        return groups

    # ------------------------------------------------------------------
    # Classification
    # ------------------------------------------------------------------

    def _classify_region(
        self, region: np.ndarray, bbox: tuple
    ) -> Optional[StairClassification]:
        x, y, rw, rh = bbox
        if rw < 10 or rh < 10:
            return None

        step_count = self._count_treads(region)
        if step_count < self.MIN_TREADS:
            return None

        has_landing = self._has_landing(region)
        stair_type = "L-shaped" if has_landing else "straight"
        direction_deg = self._detect_direction_arrow(region)
        direction_str = self._angle_to_direction(direction_deg)

        rise = 0.19   # standard US riser
        run = 0.26    # standard US tread

        cx = (x + rw / 2) * self.scale_m_per_px
        cy = (y + rh / 2) * self.scale_m_per_px

        element = StaircaseElement(
            position=Vec2(cx, cy),
            direction_degrees=direction_deg,
            step_count=step_count,
            width=rw * self.scale_m_per_px,
            rise_per_step=rise,
            run_per_step=run,
            has_landing=has_landing,
        )
        return StairClassification(
            element=element,
            confidence=0.8 if step_count >= 8 else 0.5,
            has_landing=has_landing,
            open_riser=False,
            direction=direction_str,
            stair_type=stair_type,
        )

    def _count_treads(self, region: np.ndarray) -> int:
        h_proj = region.sum(axis=1).astype(float)
        smoothed = np.convolve(h_proj, np.ones(3) / 3, mode="same")
        threshold = smoothed.max() * 0.3
        in_tread = False
        count = 0
        for val in smoothed:
            if val > threshold and not in_tread:
                count += 1
                in_tread = True
            elif val <= threshold:
                in_tread = False
        return count

    def _has_landing(self, region: np.ndarray) -> bool:
        h, w = region.shape
        mid_col = region[:, w // 2]
        gap_sizes = []
        in_gap = False
        gap_len = 0
        for px in mid_col:
            if px == 0:
                if in_gap:
                    gap_len += 1
                else:
                    in_gap = True
                    gap_len = 1
            else:
                if in_gap:
                    gap_sizes.append(gap_len)
                    in_gap = False
        # Landing creates a large gap between tread groups
        return any(g > 15 for g in gap_sizes)

    def _detect_direction_arrow(self, region: np.ndarray) -> float:
        lines = cv2.HoughLinesP(region, 1, np.pi / 180, threshold=15,
                                 minLineLength=15, maxLineGap=5)
        if lines is None:
            return 0.0
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = abs(math.degrees(math.atan2(y2 - y1, x2 - x1)))
            lo, hi = self.DIRECTION_ARROW_ANGLE_RANGE
            if lo <= angle <= hi:
                return float(angle)
        return 0.0

    def _angle_to_direction(self, angle: float) -> str:
        if 30 <= angle <= 60:
            return "up"
        if 120 <= angle <= 150:
            return "down"
        return "unknown"
