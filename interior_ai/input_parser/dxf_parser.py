"""Parse DXF CAD exports into structured architectural geometry."""

from __future__ import annotations
from pathlib import Path
from typing import Optional
import math

try:
    import ezdxf
    HAS_EZDXF = True
except ImportError:
    HAS_EZDXF = False

from ..types import Vec2, WallSegment, Opening, OpeningType, FloorPlanData


WALL_LAYERS = {"WALLS", "WALL", "A-WALL", "A-WALLS", "EXTERIOR", "INTERIOR"}
DOOR_LAYERS = {"DOORS", "DOOR", "A-DOOR", "A-DOORS"}
WINDOW_LAYERS = {"WINDOWS", "WINDOW", "A-WINDOW", "A-WINDOWS"}
STAIR_LAYERS = {"STAIRS", "STAIR", "A-STAIR", "A-STAIRS"}


class DXFParser:
    """Extract walls, doors, windows, and stairs from DXF floor plan files.

    Supports DXF versions R12 through R2018. Layer names are matched
    case-insensitively against common architectural layer naming conventions.
    """

    def __init__(self, wall_thickness_default: float = 0.2):
        if not HAS_EZDXF:
            raise ImportError("ezdxf is required: pip install ezdxf")
        self.wall_thickness_default = wall_thickness_default

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse(self, dxf_path: str | Path) -> FloorPlanData:
        """Parse a DXF file and return structured FloorPlanData."""
        dxf_path = Path(dxf_path)
        doc = ezdxf.readfile(str(dxf_path))
        msp = doc.modelspace()

        walls = self._extract_walls(msp)
        openings = self._extract_openings(msp, walls)
        scale = self._infer_scale(msp)

        plan = FloorPlanData(
            walls=walls,
            openings=openings,
            scale_m_per_px=scale,
            source_image_path=str(dxf_path),
        )
        return plan

    # ------------------------------------------------------------------
    # Extraction methods
    # ------------------------------------------------------------------

    def _extract_walls(self, msp) -> list[WallSegment]:
        walls = []
        wall_id = 0
        for entity in msp:
            layer = entity.dxf.layer.upper()
            if layer not in {l.upper() for l in WALL_LAYERS}:
                continue
            if entity.dxftype() == "LINE":
                start = entity.dxf.start
                end = entity.dxf.end
                walls.append(WallSegment(
                    start=Vec2(start.x, start.y),
                    end=Vec2(end.x, end.y),
                    thickness=self.wall_thickness_default,
                    is_exterior="EXTERIOR" in layer,
                    id=f"wall_{wall_id:04d}",
                ))
                wall_id += 1
            elif entity.dxftype() == "LWPOLYLINE":
                pts = list(entity.get_points())
                for i in range(len(pts) - 1):
                    walls.append(WallSegment(
                        start=Vec2(pts[i][0], pts[i][1]),
                        end=Vec2(pts[i+1][0], pts[i+1][1]),
                        thickness=self.wall_thickness_default,
                        is_exterior="EXTERIOR" in layer,
                        id=f"wall_{wall_id:04d}",
                    ))
                    wall_id += 1
        return walls

    def _extract_openings(self, msp, walls: list[WallSegment]) -> list[Opening]:
        openings = []
        op_id = 0
        for entity in msp:
            layer = entity.dxf.layer.upper()
            is_door = any(d in layer for d in {"DOOR"})
            is_window = any(w in layer for w in {"WINDOW"})
            if not (is_door or is_window):
                continue
            op_type = OpeningType.DOOR if is_door else OpeningType.WINDOW
            pos = self._entity_center(entity)
            if pos is None:
                continue
            nearest_wall = self._nearest_wall(pos, walls)
            if nearest_wall is None:
                continue
            t = self._project_onto_wall(pos, nearest_wall)
            width = self._entity_width(entity) or (0.9 if is_door else 1.2)
            openings.append(Opening(
                type=op_type,
                wall_id=nearest_wall.id,
                position_along_wall=t,
                width=width,
                height=2.1 if is_door else 1.2,
                sill_height=0.0 if is_door else 0.9,
            ))
            op_id += 1
        return openings

    def _infer_scale(self, msp) -> float:
        """Try to find a scale annotation or dimension to set m/unit ratio."""
        for entity in msp:
            if entity.dxftype() in ("DIMENSION",):
                try:
                    measured = entity.dxf.actual_measurement
                    if measured and measured > 0:
                        return 1.0 / measured
                except Exception:
                    pass
        return 1.0  # assume 1 unit = 1 metre if unknown

    # ------------------------------------------------------------------
    # Geometry helpers
    # ------------------------------------------------------------------

    def _entity_center(self, entity) -> Optional[Vec2]:
        try:
            if entity.dxftype() == "INSERT":
                p = entity.dxf.insert
                return Vec2(p.x, p.y)
            if entity.dxftype() == "ARC":
                p = entity.dxf.center
                return Vec2(p.x, p.y)
            if entity.dxftype() == "LINE":
                s, e = entity.dxf.start, entity.dxf.end
                return Vec2((s.x + e.x) / 2, (s.y + e.y) / 2)
        except Exception:
            pass
        return None

    def _entity_width(self, entity) -> Optional[float]:
        try:
            if entity.dxftype() == "ARC":
                return entity.dxf.radius * 2
            if entity.dxftype() == "LINE":
                s, e = entity.dxf.start, entity.dxf.end
                return math.hypot(e.x - s.x, e.y - s.y)
        except Exception:
            pass
        return None

    def _nearest_wall(self, pos: Vec2, walls: list[WallSegment]) -> Optional[WallSegment]:
        if not walls:
            return None
        best, best_dist = None, float("inf")
        for w in walls:
            d = self._point_to_segment_dist(pos, w.start, w.end)
            if d < best_dist:
                best_dist = d
                best = w
        return best if best_dist < 2.0 else None

    def _project_onto_wall(self, pos: Vec2, wall: WallSegment) -> float:
        import numpy as np
        p = pos.as_array()
        a = wall.start.as_array()
        b = wall.end.as_array()
        ab = b - a
        t = np.dot(p - a, ab) / (np.dot(ab, ab) + 1e-9)
        return float(np.clip(t, 0, 1))

    def _point_to_segment_dist(self, p: Vec2, a: Vec2, b: Vec2) -> float:
        import numpy as np
        pv = p.as_array()
        av = a.as_array()
        bv = b.as_array()
        ab = bv - av
        t = np.dot(pv - av, ab) / (np.dot(ab, ab) + 1e-9)
        t = float(np.clip(t, 0, 1))
        closest = av + t * ab
        return float(np.linalg.norm(pv - closest))
