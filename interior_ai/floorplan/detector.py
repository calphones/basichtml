"""Computer-vision pipeline: detect walls, doors, windows, stairs from raster images."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import numpy as np

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

from ..types import Vec2, WallSegment, Opening, OpeningType, StaircaseElement


@dataclass
class DetectionResult:
    walls: list[WallSegment]
    openings: list[Opening]
    stairs: list[StaircaseElement]
    room_mask: Optional[np.ndarray]  # labelled room regions
    debug_image: Optional[np.ndarray] = None


class FloorPlanDetector:
    """Multi-stage CV detector for floor plan elements.

    Pipeline:
    1. Binarise input (adaptive threshold on pre-processed grayscale).
    2. Morphological ops to isolate wall pixels.
    3. Probabilistic Hough line detection for wall segments.
    4. Arc template matching for door swings.
    5. Rectangle clustering for windows.
    6. Stair pattern detection via periodic parallel lines.
    7. Flood-fill segmentation for room labelling.
    """

    # Tuning constants (pixels at 300 DPI)
    MIN_WALL_LEN_PX: int = 30
    MAX_WALL_GAP_PX: int = 8
    WALL_THICKNESS_RANGE: tuple[int, int] = (3, 40)
    DOOR_ARC_RADII: tuple[int, int] = (20, 100)
    STAIR_LINE_SPACING_RANGE: tuple[int, int] = (8, 25)
    STAIR_MIN_LINES: int = 5

    def __init__(self, scale_m_per_px: float = 1.0):
        if not HAS_CV2:
            raise ImportError("opencv-python is required")
        self.scale_m_per_px = scale_m_per_px

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect(self, image: np.ndarray, debug: bool = False) -> DetectionResult:
        """Run full detection pipeline on a pre-processed binary image."""
        binary = self._binarise(image)
        wall_mask = self._extract_wall_mask(binary)
        walls = self._detect_walls(wall_mask)
        openings = self._detect_doors(binary, walls) + self._detect_windows(binary, walls)
        stairs = self._detect_stairs(binary)
        room_mask = self._segment_rooms(wall_mask)
        debug_img = self._draw_debug(image, walls, openings, stairs) if debug else None
        return DetectionResult(
            walls=walls,
            openings=openings,
            stairs=stairs,
            room_mask=room_mask,
            debug_image=debug_img,
        )

    # ------------------------------------------------------------------
    # Stage 1: Binarisation
    # ------------------------------------------------------------------

    def _binarise(self, image: np.ndarray) -> np.ndarray:
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image.copy()
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        binary = cv2.adaptiveThreshold(
            blurred, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            blockSize=15, C=6,
        )
        return binary

    # ------------------------------------------------------------------
    # Stage 2: Wall mask
    # ------------------------------------------------------------------

    def _extract_wall_mask(self, binary: np.ndarray) -> np.ndarray:
        lo, hi = self.WALL_THICKNESS_RANGE
        # Close small gaps within wall thickness range
        for k_size in range(lo, hi, 4):
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (k_size, 1))
            binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, k_size))
            binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        return binary

    # ------------------------------------------------------------------
    # Stage 3: Wall segments via Hough
    # ------------------------------------------------------------------

    def _detect_walls(self, wall_mask: np.ndarray) -> list[WallSegment]:
        lines = cv2.HoughLinesP(
            wall_mask,
            rho=1,
            theta=np.pi / 180,
            threshold=40,
            minLineLength=self.MIN_WALL_LEN_PX,
            maxLineGap=self.MAX_WALL_GAP_PX,
        )
        if lines is None:
            return []
        merged = self._merge_collinear(lines)
        walls = []
        for i, (x1, y1, x2, y2) in enumerate(merged):
            sx = x1 * self.scale_m_per_px
            sy = y1 * self.scale_m_per_px
            ex = x2 * self.scale_m_per_px
            ey = y2 * self.scale_m_per_px
            walls.append(WallSegment(
                start=Vec2(sx, sy),
                end=Vec2(ex, ey),
                thickness=0.15 * self.scale_m_per_px * 100,
                id=f"wall_{i:04d}",
            ))
        return walls

    # ------------------------------------------------------------------
    # Stage 4: Door detection (arc sweeps)
    # ------------------------------------------------------------------

    def _detect_doors(self, binary: np.ndarray, walls: list[WallSegment]) -> list[Opening]:
        openings = []
        circles = cv2.HoughCircles(
            binary,
            cv2.HOUGH_GRADIENT,
            dp=1.5,
            minDist=30,
            param1=50,
            param2=25,
            minRadius=self.DOOR_ARC_RADII[0],
            maxRadius=self.DOOR_ARC_RADII[1],
        )
        if circles is None:
            return []
        circles = np.round(circles[0]).astype(int)
        for i, (cx, cy, r) in enumerate(circles):
            pos = Vec2(cx * self.scale_m_per_px, cy * self.scale_m_per_px)
            nearest = self._nearest_wall(pos, walls)
            if nearest is None:
                continue
            t = self._project_t(pos, nearest)
            width = 2 * r * self.scale_m_per_px
            openings.append(Opening(
                type=OpeningType.DOOR,
                wall_id=nearest.id,
                position_along_wall=t,
                width=max(0.7, min(1.2, width)),
                height=2.1,
                sill_height=0.0,
            ))
        return openings

    # ------------------------------------------------------------------
    # Stage 5: Window detection (thin rectangles in walls)
    # ------------------------------------------------------------------

    def _detect_windows(self, binary: np.ndarray, walls: list[WallSegment]) -> list[Opening]:
        openings = []
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            aspect = max(w, h) / (min(w, h) + 1)
            area = w * h
            # Windows are thin rectangles: aspect > 4, small area
            if aspect > 4 and 200 < area < 15000:
                cx = (x + w / 2) * self.scale_m_per_px
                cy = (y + h / 2) * self.scale_m_per_px
                pos = Vec2(cx, cy)
                nearest = self._nearest_wall(pos, walls)
                if nearest is None:
                    continue
                t = self._project_t(pos, nearest)
                width_m = max(w, h) * self.scale_m_per_px
                openings.append(Opening(
                    type=OpeningType.WINDOW,
                    wall_id=nearest.id,
                    position_along_wall=t,
                    width=max(0.6, min(3.0, width_m)),
                    height=1.2,
                    sill_height=0.9,
                ))
        return openings

    # ------------------------------------------------------------------
    # Stage 6: Stair detection
    # ------------------------------------------------------------------

    def _detect_stairs(self, binary: np.ndarray) -> list[StaircaseElement]:
        stairs = []
        lines = cv2.HoughLinesP(
            binary, 1, np.pi / 180, threshold=25,
            minLineLength=20, maxLineGap=3,
        )
        if lines is None:
            return []
        h_lines = [l[0] for l in lines if abs(l[0][3] - l[0][1]) < 5]
        if len(h_lines) < self.STAIR_MIN_LINES:
            return []
        h_lines.sort(key=lambda l: l[1])
        spacings = [h_lines[i+1][1] - h_lines[i][1] for i in range(len(h_lines)-1)]
        if not spacings:
            return []
        med_spacing = float(np.median(spacings))
        lo, hi = self.STAIR_LINE_SPACING_RANGE
        if not (lo <= med_spacing <= hi):
            return []
        ys = [l[1] for l in h_lines]
        xs = [l[0] for l in h_lines]
        cx = float(np.mean(xs)) * self.scale_m_per_px
        cy = float(np.mean(ys)) * self.scale_m_per_px
        stairs.append(StaircaseElement(
            position=Vec2(cx, cy),
            direction_degrees=0.0,
            step_count=len(h_lines),
        ))
        return stairs

    # ------------------------------------------------------------------
    # Stage 7: Room segmentation
    # ------------------------------------------------------------------

    def _segment_rooms(self, wall_mask: np.ndarray) -> np.ndarray:
        inverted = cv2.bitwise_not(wall_mask)
        # Dilate walls slightly to close thin gaps before flood fill
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        closed = cv2.morphologyEx(inverted, cv2.MORPH_ERODE, kernel)
        n_labels, labels = cv2.connectedComponents(closed)
        return labels.astype(np.int32)

    # ------------------------------------------------------------------
    # Geometry helpers
    # ------------------------------------------------------------------

    def _merge_collinear(self, lines: np.ndarray) -> list[tuple]:
        """Merge nearly-collinear Hough line segments."""
        segments = [tuple(l[0]) for l in lines]
        merged = []
        used = [False] * len(segments)
        for i, seg in enumerate(segments):
            if used[i]:
                continue
            group = [seg]
            for j, other in enumerate(segments[i+1:], i+1):
                if not used[j] and self._segments_collinear(seg, other):
                    group.append(other)
                    used[j] = True
            used[i] = True
            merged.append(self._merge_group(group))
        return merged

    def _segments_collinear(self, a, b, dist_thresh=8.0, angle_thresh=5.0) -> bool:
        ax1, ay1, ax2, ay2 = a
        bx1, by1, bx2, by2 = b
        ang_a = np.degrees(np.arctan2(ay2 - ay1, ax2 - ax1)) % 180
        ang_b = np.degrees(np.arctan2(by2 - by1, bx2 - bx1)) % 180
        if abs(ang_a - ang_b) > angle_thresh:
            return False
        # Check midpoint distance
        ma = np.array([(ax1 + ax2) / 2, (ay1 + ay2) / 2])
        mb = np.array([(bx1 + bx2) / 2, (by1 + by2) / 2])
        return float(np.linalg.norm(ma - mb)) < 60

    def _merge_group(self, group: list[tuple]) -> tuple:
        xs = [g[0] for g in group] + [g[2] for g in group]
        ys = [g[1] for g in group] + [g[3] for g in group]
        return (min(xs), ys[xs.index(min(xs))], max(xs), ys[xs.index(max(xs))])

    def _nearest_wall(self, pos: Vec2, walls: list[WallSegment]):
        if not walls:
            return None
        best, best_d = None, float("inf")
        for w in walls:
            d = self._pt_seg(pos, w.start, w.end)
            if d < best_d:
                best_d, best = d, w
        return best if best_d < 2.0 else None

    def _project_t(self, pos: Vec2, wall: WallSegment) -> float:
        p = pos.as_array()
        a, b = wall.start.as_array(), wall.end.as_array()
        ab = b - a
        t = float(np.dot(p - a, ab) / (np.dot(ab, ab) + 1e-9))
        return max(0.0, min(1.0, t))

    def _pt_seg(self, p: Vec2, a: Vec2, b: Vec2) -> float:
        pv, av, bv = p.as_array(), a.as_array(), b.as_array()
        ab = bv - av
        t = float(np.clip(np.dot(pv - av, ab) / (np.dot(ab, ab) + 1e-9), 0, 1))
        return float(np.linalg.norm(pv - (av + t * ab)))

    # ------------------------------------------------------------------
    # Debug visualisation
    # ------------------------------------------------------------------

    def _draw_debug(self, image: np.ndarray, walls, openings, stairs) -> np.ndarray:
        out = image.copy() if len(image.shape) == 3 else cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        for w in walls:
            x1 = int(w.start.x / self.scale_m_per_px)
            y1 = int(w.start.y / self.scale_m_per_px)
            x2 = int(w.end.x / self.scale_m_per_px)
            y2 = int(w.end.y / self.scale_m_per_px)
            cv2.line(out, (x1, y1), (x2, y2), (0, 128, 255), 2)
        for s in stairs:
            cx = int(s.position.x / self.scale_m_per_px)
            cy = int(s.position.y / self.scale_m_per_px)
            cv2.circle(out, (cx, cy), 15, (255, 0, 0), 3)
        return out
