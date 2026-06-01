"""Parse IFC BIM models into FloorPlanData."""

from __future__ import annotations
from pathlib import Path
import math

try:
    import ifcopenshell
    import ifcopenshell.geom
    import ifcopenshell.util.placement
    HAS_IFC = True
except ImportError:
    HAS_IFC = False

try:
    import numpy as np
    HAS_NP = True
except ImportError:
    HAS_NP = False

from ..types import (
    Vec2, Vec3, WallSegment, Opening, OpeningType,
    StaircaseElement, Room, RoomType, FloorPlanData
)


class IFCParser:
    """Extract architectural geometry from IFC 2x3/4 BIM files.

    Reads IfcWall, IfcDoor, IfcWindow, IfcStair, and IfcSpace entities and
    maps them to the system's internal types.
    """

    def __init__(self):
        if not HAS_IFC:
            raise ImportError("ifcopenshell is required: pip install ifcopenshell")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse(self, ifc_path: str | Path) -> FloorPlanData:
        ifc_path = Path(ifc_path)
        model = ifcopenshell.open(str(ifc_path))

        walls = self._extract_walls(model)
        openings = self._extract_openings(model, walls)
        stairs = self._extract_stairs(model)
        rooms = self._extract_spaces(model)

        return FloorPlanData(
            rooms=rooms,
            walls=walls,
            openings=openings,
            stairs=stairs,
            scale_m_per_px=1.0,
            source_image_path=str(ifc_path),
        )

    # ------------------------------------------------------------------
    # Extraction
    # ------------------------------------------------------------------

    def _extract_walls(self, model) -> list[WallSegment]:
        walls = []
        settings = ifcopenshell.geom.settings()
        settings.set(settings.USE_WORLD_COORDS, True)
        for wall in model.by_type("IfcWall"):
            try:
                shape = ifcopenshell.geom.create_shape(settings, wall)
                verts = shape.geometry.verts   # flat list: x0,y0,z0,x1,y1,z1,...
                pts = [(verts[i], verts[i+1]) for i in range(0, len(verts), 3)]
                if len(pts) < 2:
                    continue
                xs = [p[0] for p in pts]
                ys = [p[1] for p in pts]
                start = Vec2(min(xs), ys[xs.index(min(xs))])
                end = Vec2(max(xs), ys[xs.index(max(xs))])
                walls.append(WallSegment(
                    start=start, end=end,
                    thickness=0.2,
                    id=wall.GlobalId,
                ))
            except Exception:
                continue
        return walls

    def _extract_openings(self, model, walls: list[WallSegment]) -> list[Opening]:
        openings = []
        settings = ifcopenshell.geom.settings()
        settings.set(settings.USE_WORLD_COORDS, True)
        for entity_type, op_type in [("IfcDoor", OpeningType.DOOR),
                                      ("IfcWindow", OpeningType.WINDOW)]:
            for entity in model.by_type(entity_type):
                try:
                    shape = ifcopenshell.geom.create_shape(settings, entity)
                    verts = shape.geometry.verts
                    xs = verts[0::3]
                    ys = verts[1::3]
                    cx, cy = sum(xs)/len(xs), sum(ys)/len(ys)
                    pos = Vec2(cx, cy)
                    nearest = self._nearest_wall(pos, walls)
                    if nearest is None:
                        continue
                    t = self._project_onto_wall(pos, nearest)
                    width = max(xs) - min(xs) if xs else (0.9 if op_type == OpeningType.DOOR else 1.2)
                    openings.append(Opening(
                        type=op_type,
                        wall_id=nearest.id,
                        position_along_wall=t,
                        width=max(0.5, width),
                        height=2.1 if op_type == OpeningType.DOOR else 1.2,
                        sill_height=0.0 if op_type == OpeningType.DOOR else 0.9,
                    ))
                except Exception:
                    continue
        return openings

    def _extract_stairs(self, model) -> list[StaircaseElement]:
        stairs = []
        for stair in model.by_type("IfcStair"):
            try:
                mat = ifcopenshell.util.placement.get_local_placement(
                    stair.ObjectPlacement
                )
                x, y = float(mat[0][3]), float(mat[1][3])
                stairs.append(StaircaseElement(
                    position=Vec2(x, y),
                    direction_degrees=0.0,
                ))
            except Exception:
                continue
        return stairs

    def _extract_spaces(self, model) -> list[Room]:
        rooms = []
        for space in model.by_type("IfcSpace"):
            try:
                name = (space.Name or "").lower()
                room_type = self._classify_room(name)
                rooms.append(Room(
                    id=space.GlobalId,
                    type=room_type,
                    polygon=[],
                    label=space.Name or "",
                ))
            except Exception:
                continue
        return rooms

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _classify_room(self, name: str) -> RoomType:
        mapping = {
            "living": RoomType.LIVING_ROOM,
            "dining": RoomType.DINING_ROOM,
            "kitchen": RoomType.KITCHEN,
            "bed": RoomType.BEDROOM,
            "bath": RoomType.BATHROOM,
            "hall": RoomType.HALLWAY,
            "foyer": RoomType.FOYER,
            "office": RoomType.OFFICE,
            "laundry": RoomType.LAUNDRY,
            "garage": RoomType.GARAGE,
        }
        for key, rtype in mapping.items():
            if key in name:
                return rtype
        return RoomType.UNKNOWN

    def _nearest_wall(self, pos: Vec2, walls: list[WallSegment]):
        if not walls:
            return None
        best, best_dist = None, float("inf")
        for w in walls:
            d = self._pt_seg_dist(pos, w.start, w.end)
            if d < best_dist:
                best_dist, best = d, w
        return best if best_dist < 3.0 else None

    def _project_onto_wall(self, pos: Vec2, wall: WallSegment) -> float:
        import numpy as np
        p = pos.as_array()
        a, b = wall.start.as_array(), wall.end.as_array()
        ab = b - a
        t = float(np.dot(p - a, ab) / (np.dot(ab, ab) + 1e-9))
        return max(0.0, min(1.0, t))

    def _pt_seg_dist(self, p: Vec2, a: Vec2, b: Vec2) -> float:
        import numpy as np
        pv, av, bv = p.as_array(), a.as_array(), b.as_array()
        ab = bv - av
        t = float(np.clip(np.dot(pv - av, ab) / (np.dot(ab, ab) + 1e-9), 0, 1))
        return float(np.linalg.norm(pv - (av + t * ab)))
