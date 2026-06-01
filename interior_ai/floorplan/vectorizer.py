"""Convert raw detected geometry into clean vectorised room polygons."""

from __future__ import annotations
import numpy as np
from typing import Optional

try:
    from shapely.geometry import Polygon, LineString, MultiLineString
    from shapely.ops import unary_union, polygonize
    HAS_SHAPELY = True
except ImportError:
    HAS_SHAPELY = False

try:
    import networkx as nx
    HAS_NX = True
except ImportError:
    HAS_NX = False

from ..types import Vec2, WallSegment, Room, RoomType, FloorPlanData


class Vectorizer:
    """Convert a list of wall segments into closed room polygons.

    Approach:
    1. Snap nearby wall endpoints to a tolerance grid.
    2. Build a planar graph from wall segment intersections.
    3. Find minimum cycles (rooms) using Shapely polygonize.
    4. Filter polygons by minimum area and aspect ratio.
    5. Assign room types from OCR label proximity.
    """

    SNAP_TOLERANCE_M: float = 0.05   # 5 cm

    def __init__(self, snap_tolerance: float = SNAP_TOLERANCE_M):
        self.snap_tolerance = snap_tolerance

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def vectorize(self, floor_plan: FloorPlanData) -> FloorPlanData:
        """Populate floor_plan.rooms from floor_plan.walls in-place."""
        if not HAS_SHAPELY:
            raise ImportError("shapely is required: pip install shapely")
        snapped = self._snap_endpoints(floor_plan.walls)
        lines = [LineString([(w.start.x, w.start.y), (w.end.x, w.end.y)]) for w in snapped]
        if not lines:
            return floor_plan
        polygons = list(polygonize(lines))
        rooms = []
        for i, poly in enumerate(polygons):
            if not poly.is_valid or poly.area < 1.0:  # minimum 1 m²
                continue
            exterior_pts = list(poly.exterior.coords)
            verts = [Vec2(x, y) for x, y in exterior_pts[:-1]]
            room = Room(
                id=f"room_{i:03d}",
                type=RoomType.UNKNOWN,
                polygon=verts,
                ceiling_height=2.7,
            )
            room.compute_area()
            rooms.append(room)
        floor_plan.rooms = rooms
        return floor_plan

    def assign_room_types(
        self,
        floor_plan: FloorPlanData,
        label_map: dict[tuple[float, float], str],
    ) -> FloorPlanData:
        """Map OCR-detected room labels to Room.type by spatial proximity."""
        for room in floor_plan.rooms:
            centroid = room.centroid
            best_label, best_dist = "", float("inf")
            for (lx, ly), label in label_map.items():
                d = Vec2(lx, ly).distance_to(centroid)
                if d < best_dist:
                    best_dist, best_label = d, label
            if best_label:
                room.type = self._classify_label(best_label)
                room.label = best_label
        return floor_plan

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _snap_endpoints(self, walls: list[WallSegment]) -> list[WallSegment]:
        """Snap nearby endpoints to the same coordinate within tolerance."""
        pts: list[Vec2] = []
        for w in walls:
            pts.extend([w.start, w.end])

        def snap(p: Vec2) -> Vec2:
            for q in pts:
                if p is not q and p.distance_to(q) < self.snap_tolerance:
                    return q
            return p

        snapped = []
        for w in walls:
            snapped.append(WallSegment(
                start=snap(w.start),
                end=snap(w.end),
                thickness=w.thickness,
                height=w.height,
                is_exterior=w.is_exterior,
                id=w.id,
            ))
        return snapped

    def _classify_label(self, label: str) -> RoomType:
        label_lower = label.lower().strip()
        mapping = {
            "living": RoomType.LIVING_ROOM,
            "great room": RoomType.LIVING_ROOM,
            "family": RoomType.LIVING_ROOM,
            "dining": RoomType.DINING_ROOM,
            "kitchen": RoomType.KITCHEN,
            "master bed": RoomType.BEDROOM,
            "bed": RoomType.BEDROOM,
            "bath": RoomType.BATHROOM,
            "powder": RoomType.BATHROOM,
            "hall": RoomType.HALLWAY,
            "foyer": RoomType.FOYER,
            "entry": RoomType.FOYER,
            "office": RoomType.OFFICE,
            "study": RoomType.OFFICE,
            "laundry": RoomType.LAUNDRY,
            "garage": RoomType.GARAGE,
        }
        for key, rtype in mapping.items():
            if key in label_lower:
                return rtype
        return RoomType.UNKNOWN
