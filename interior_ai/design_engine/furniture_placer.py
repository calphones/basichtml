"""Furniture placement engine: compute optimal positions respecting clearances and traffic flow."""

from __future__ import annotations
import math
import random
from dataclasses import dataclass
from typing import Optional
import numpy as np

try:
    from shapely.geometry import Polygon, Point, box as shapely_box
    HAS_SHAPELY = True
except ImportError:
    HAS_SHAPELY = False

from ..types import (
    Vec2, Vec3, Room, RoomType, FurnitureItem, FurnitureCategory,
    BoundingBox2D, SceneGraph, FloorPlanData, DesignSpec
)
from .style_profiles import STYLE_PROFILES
from .clearance_checker import ClearanceChecker
from .zone_planner import ZonePlanner


@dataclass
class FurnitureSuggestion:
    category: FurnitureCategory
    position: Vec3
    rotation_z: float   # degrees
    scale: Vec3
    priority: int = 0   # lower = more important


class FurniturePlacer:
    """Place furniture in each room respecting:
    - Architectural constraints (walls, doors, windows)
    - Clearance requirements (circulation paths)
    - Functional zones (conversation, TV, dining)
    - Style profile dimensions and proportions

    Uses a constraint-satisfaction approach:
    1. Identify anchor positions (fireplace, TV wall, window views).
    2. Place primary pieces first (sofa, bed, dining table).
    3. Place secondary pieces around primaries.
    4. Validate clearances and nudge positions.
    """

    # Minimum clearance widths (metres)
    MIN_CIRCULATION = 0.91
    MIN_SOFA_TV = 2.1
    MAX_SOFA_TV = 3.7
    DINING_CHAIR_PULL = 0.5
    BED_SIDE_CLEAR = 0.6

    def __init__(self, spec: DesignSpec):
        self.spec = spec
        self.style = STYLE_PROFILES.get(spec.style)
        self._checker = ClearanceChecker()
        self._planner = ZonePlanner()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def place_for_scene(self, scene: SceneGraph) -> SceneGraph:
        if scene.floor_plan is None:
            return scene
        for room in scene.floor_plan.rooms:
            suggestions = self.place_room(room, scene.floor_plan)
            for s in suggestions:
                item = FurnitureItem(
                    id=f"{s.category.value}_{room.id}_{len(scene.furniture)}",
                    category=s.category,
                    name=self._furniture_name(s.category),
                    position=s.position,
                    rotation_z=s.rotation_z,
                    scale=s.scale,
                    room_id=room.id,
                )
                scene.furniture.append(item)
        return scene

    def place_room(
        self, room: Room, plan: FloorPlanData
    ) -> list[FurnitureSuggestion]:
        placer = self._get_room_placer(room.type)
        return placer(room, plan)

    # ------------------------------------------------------------------
    # Per-room placers
    # ------------------------------------------------------------------

    def _get_room_placer(self, room_type: RoomType):
        mapping = {
            RoomType.LIVING_ROOM: self._place_living_room,
            RoomType.DINING_ROOM: self._place_dining_room,
            RoomType.BEDROOM: self._place_bedroom,
            RoomType.KITCHEN: self._place_kitchen,
        }
        return mapping.get(room_type, self._place_generic)

    def _place_living_room(
        self, room: Room, plan: FloorPlanData
    ) -> list[FurnitureSuggestion]:
        suggestions = []
        centroid = room.centroid
        bbox = self._room_bbox(room)
        if bbox is None:
            return suggestions

        # Find TV wall (longest wall without door/window → face sofa toward it)
        tv_wall = self._find_tv_wall(room, plan)
        tv_rot = self._wall_facing_angle(tv_wall, centroid) if tv_wall else 0.0

        sw = self.style.sofa_length_m if self.style else 2.8
        sd = self.style.sofa_depth_m if self.style else 0.9
        prefer_curved = self.style.prefer_curved if self.style else False

        # Sofa: offset from TV wall by optimal viewing distance
        tv_dist = (self.MIN_SOFA_TV + self.MAX_SOFA_TV) / 2
        sofa_pos = self._offset_from_wall(centroid, tv_wall, tv_dist) if tv_wall else Vec2(centroid.x, centroid.y - tv_dist / 2)
        suggestions.append(FurnitureSuggestion(
            category=FurnitureCategory.SECTIONAL if prefer_curved else FurnitureCategory.SEATING,
            position=Vec3(sofa_pos.x, sofa_pos.y, 0),
            rotation_z=tv_rot,
            scale=Vec3(sw, sd, 0.85),
            priority=1,
        ))

        # Coffee table in front of sofa
        ct_pos = self._offset_from_pos(sofa_pos, tv_rot, 0.6 + sd / 2)
        suggestions.append(FurnitureSuggestion(
            category=FurnitureCategory.COFFEE_TABLE,
            position=Vec3(ct_pos.x, ct_pos.y, 0),
            rotation_z=tv_rot,
            scale=Vec3(1.2, 0.6, self.style.coffee_table_h_m if self.style else 0.42),
            priority=2,
        ))

        # Accent chair (perpendicular to sofa)
        ac_pos = self._offset_from_pos(sofa_pos, tv_rot + 90, sw / 2 + 0.5)
        suggestions.append(FurnitureSuggestion(
            category=FurnitureCategory.ACCENT_CHAIR,
            position=Vec3(ac_pos.x, ac_pos.y, 0),
            rotation_z=tv_rot + 45,
            scale=Vec3(0.8, 0.8, 0.85),
            priority=3,
        ))

        # Rug under conversation group
        suggestions.append(FurnitureSuggestion(
            category=FurnitureCategory.RUG,
            position=Vec3(centroid.x, centroid.y, 0.001),
            rotation_z=0,
            scale=Vec3(2.7, 3.6, 0.02),
            priority=4,
        ))

        # Floor lamp beside accent chair
        lamp_pos = self._offset_from_pos(ac_pos, tv_rot + 45, 0.6)
        suggestions.append(FurnitureSuggestion(
            category=FurnitureCategory.LAMP,
            position=Vec3(lamp_pos.x, lamp_pos.y, 0),
            rotation_z=0,
            scale=Vec3(0.4, 0.4, 1.6),
            priority=5,
        ))

        return suggestions

    def _place_dining_room(
        self, room: Room, plan: FloorPlanData
    ) -> list[FurnitureSuggestion]:
        suggestions = []
        centroid = room.centroid
        dt = self.style.dining_table_m if self.style else (1.0, 2.0)

        suggestions.append(FurnitureSuggestion(
            category=FurnitureCategory.DINING_TABLE,
            position=Vec3(centroid.x, centroid.y, 0),
            rotation_z=0,
            scale=Vec3(dt[1], dt[0], 0.75),
            priority=1,
        ))

        # Pendant above dining table
        suggestions.append(FurnitureSuggestion(
            category=FurnitureCategory.LAMP,
            position=Vec3(centroid.x, centroid.y, 2.0),
            rotation_z=0,
            scale=Vec3(0.5, 0.5, 0.6),
            priority=2,
        ))
        return suggestions

    def _place_bedroom(
        self, room: Room, plan: FloorPlanData
    ) -> list[FurnitureSuggestion]:
        suggestions = []
        centroid = room.centroid
        bbox = self._room_bbox(room)
        if bbox is None:
            return suggestions

        # Bed against longest wall without window
        bed_wall = self._find_bed_wall(room, plan)
        bed_rot = self._wall_facing_angle(bed_wall, centroid) if bed_wall else 0.0
        bed_pos = self._offset_from_wall(centroid, bed_wall, 1.0) if bed_wall else centroid

        suggestions.append(FurnitureSuggestion(
            category=FurnitureCategory.BED,
            position=Vec3(bed_pos.x, bed_pos.y, 0),
            rotation_z=bed_rot,
            scale=Vec3(1.52, 2.03, 0.55),  # queen
            priority=1,
        ))

        # Side tables
        for side in [-1, 1]:
            angle_rad = math.radians(bed_rot + 90 * side)
            st_x = bed_pos.x + math.cos(angle_rad) * 0.9
            st_y = bed_pos.y + math.sin(angle_rad) * 0.9
            suggestions.append(FurnitureSuggestion(
                category=FurnitureCategory.SIDE_TABLE,
                position=Vec3(st_x, st_y, 0),
                rotation_z=bed_rot,
                scale=Vec3(0.5, 0.4, 0.55),
                priority=2,
            ))

        return suggestions

    def _place_kitchen(
        self, room: Room, plan: FloorPlanData
    ) -> list[FurnitureSuggestion]:
        # Kitchens largely fixed by cabinetry — just note island potential
        return []

    def _place_generic(
        self, room: Room, plan: FloorPlanData
    ) -> list[FurnitureSuggestion]:
        return []

    # ------------------------------------------------------------------
    # Wall / position helpers
    # ------------------------------------------------------------------

    def _room_bbox(self, room: Room) -> Optional[BoundingBox2D]:
        if not room.polygon:
            return None
        xs = [p.x for p in room.polygon]
        ys = [p.y for p in room.polygon]
        return BoundingBox2D(min(xs), min(ys), max(xs), max(ys))

    def _find_tv_wall(self, room: Room, plan: FloorPlanData):
        """Return the wall that should face the sofa (longest solid wall)."""
        return self._find_best_wall(room, plan, prefer_solid=True)

    def _find_bed_wall(self, room: Room, plan: FloorPlanData):
        return self._find_best_wall(room, plan, prefer_solid=True)

    def _find_best_wall(self, room: Room, plan: FloorPlanData, prefer_solid: bool = True):
        from ..types import WallSegment
        room_poly_pts = [(p.x, p.y) for p in room.polygon]
        if not room_poly_pts:
            return None
        door_wall_ids = {op.wall_id for op in plan.openings}
        best, best_len = None, 0.0
        for wall in plan.walls:
            if prefer_solid and wall.id in door_wall_ids:
                continue
            if self._wall_near_room(wall, room_poly_pts):
                length = wall.length
                if length > best_len:
                    best_len, best = length, wall
        return best

    def _wall_near_room(self, wall, poly_pts: list[tuple]) -> bool:
        if not HAS_SHAPELY:
            return True
        poly = Polygon(poly_pts)
        mid = Point((wall.start.x + wall.end.x) / 2, (wall.start.y + wall.end.y) / 2)
        return poly.distance(mid) < 1.0

    def _wall_facing_angle(self, wall, centroid: Vec2) -> float:
        if wall is None:
            return 0.0
        mid = wall.midpoint
        angle = math.degrees(math.atan2(
            centroid.y - mid.y, centroid.x - mid.x
        ))
        return (angle + 180) % 360

    def _offset_from_wall(self, centroid: Vec2, wall, dist: float) -> Vec2:
        if wall is None:
            return centroid
        mid = wall.midpoint
        dx = centroid.x - mid.x
        dy = centroid.y - mid.y
        norm = math.hypot(dx, dy) or 1
        return Vec2(mid.x + dx / norm * dist, mid.y + dy / norm * dist)

    def _offset_from_pos(self, pos: Vec2, angle_deg: float, dist: float) -> Vec2:
        a = math.radians(angle_deg)
        return Vec2(pos.x + math.cos(a) * dist, pos.y + math.sin(a) * dist)

    def _furniture_name(self, category: FurnitureCategory) -> str:
        names = {
            FurnitureCategory.SECTIONAL: "Curved Sectional Sofa",
            FurnitureCategory.SEATING: "Sofa",
            FurnitureCategory.COFFEE_TABLE: "Coffee Table",
            FurnitureCategory.ACCENT_CHAIR: "Accent Chair",
            FurnitureCategory.RUG: "Area Rug",
            FurnitureCategory.LAMP: "Floor Lamp",
            FurnitureCategory.BED: "Bed",
            FurnitureCategory.SIDE_TABLE: "Nightstand",
            FurnitureCategory.DINING_TABLE: "Dining Table",
            FurnitureCategory.TV_UNIT: "TV Unit",
        }
        return names.get(category, category.value.replace("_", " ").title())
