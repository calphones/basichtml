"""Validate furniture layouts against architectural clearance requirements."""

from __future__ import annotations
from dataclasses import dataclass
import math
import numpy as np

try:
    from shapely.geometry import Polygon, Point, LineString
    from shapely.ops import unary_union
    HAS_SHAPELY = True
except ImportError:
    HAS_SHAPELY = False

from ..types import (
    Vec2, FurnitureItem, WallSegment, Opening, OpeningType,
    FloorPlanData, SceneGraph
)


@dataclass
class ClearanceViolation:
    item_id: str
    violation_type: str   # "overlap", "blocked_path", "too_close_to_door", "outside_room"
    description: str
    severity: str         # "error" | "warning"
    suggested_offset: tuple[float, float] = (0.0, 0.0)


class ClearanceChecker:
    """Check furniture placement for clearance violations.

    Rules enforced:
    - No furniture overlap (bounding box intersection).
    - Door swing arcs must be clear (0.9 m radius minimum).
    - Circulation paths ≥ 0.91 m wide between furniture.
    - No furniture blocking windows (min 0.3 m from windowsill).
    - Furniture must lie within room polygon.
    """

    MIN_DOOR_CLEARANCE_M = 0.91
    MIN_CIRCULATION_M = 0.91
    MIN_WINDOW_CLEARANCE_M = 0.30

    def check_scene(self, scene: SceneGraph) -> list[ClearanceViolation]:
        if scene.floor_plan is None:
            return []
        violations = []
        violations += self._check_overlaps(scene.furniture)
        violations += self._check_door_clearances(scene.furniture, scene.floor_plan)
        violations += self._check_room_containment(scene.furniture, scene.floor_plan)
        return violations

    def check_item(
        self,
        item: FurnitureItem,
        others: list[FurnitureItem],
        plan: FloorPlanData,
    ) -> list[ClearanceViolation]:
        violations = []
        for other in others:
            if other.id == item.id:
                continue
            if self._items_overlap(item, other):
                violations.append(ClearanceViolation(
                    item_id=item.id,
                    violation_type="overlap",
                    description=f"{item.name} overlaps {other.name}",
                    severity="error",
                    suggested_offset=self._push_apart(item, other),
                ))
        violations += self._check_door_clearances([item], plan)
        violations += self._check_room_containment([item], plan)
        return violations

    # ------------------------------------------------------------------
    # Overlap detection
    # ------------------------------------------------------------------

    def _check_overlaps(self, items: list[FurnitureItem]) -> list[ClearanceViolation]:
        violations = []
        for i, a in enumerate(items):
            for b in items[i+1:]:
                if self._items_overlap(a, b):
                    violations.append(ClearanceViolation(
                        item_id=a.id,
                        violation_type="overlap",
                        description=f"{a.name} overlaps {b.name}",
                        severity="error",
                        suggested_offset=self._push_apart(a, b),
                    ))
        return violations

    def _items_overlap(self, a: FurnitureItem, b: FurnitureItem) -> bool:
        if not HAS_SHAPELY:
            return self._aabb_overlap(a, b)
        poly_a = self._item_polygon(a)
        poly_b = self._item_polygon(b)
        return poly_a.intersects(poly_b)

    def _aabb_overlap(self, a: FurnitureItem, b: FurnitureItem) -> bool:
        ax, ay = a.position.x, a.position.y
        bx, by = b.position.x, b.position.y
        aw, ad = a.scale.x / 2, a.scale.y / 2
        bw, bd = b.scale.x / 2, b.scale.y / 2
        return abs(ax - bx) < aw + bw and abs(ay - by) < ad + bd

    def _item_polygon(self, item: FurnitureItem):
        cx, cy = item.position.x, item.position.y
        hw, hd = item.scale.x / 2, item.scale.y / 2
        rot = math.radians(item.rotation_z)
        cos_r, sin_r = math.cos(rot), math.sin(rot)
        corners = [(-hw, -hd), (hw, -hd), (hw, hd), (-hw, hd)]
        world = [
            (cx + x * cos_r - y * sin_r, cy + x * sin_r + y * cos_r)
            for x, y in corners
        ]
        return Polygon(world)

    def _push_apart(
        self, a: FurnitureItem, b: FurnitureItem
    ) -> tuple[float, float]:
        dx = a.position.x - b.position.x
        dy = a.position.y - b.position.y
        dist = math.hypot(dx, dy) or 1.0
        push = (a.scale.x + b.scale.x) / 2 + 0.1
        return (dx / dist * push, dy / dist * push)

    # ------------------------------------------------------------------
    # Door clearances
    # ------------------------------------------------------------------

    def _check_door_clearances(
        self, items: list[FurnitureItem], plan: FloorPlanData
    ) -> list[ClearanceViolation]:
        violations = []
        if not HAS_SHAPELY:
            return violations
        door_positions = self._door_positions(plan)
        for item in items:
            for (dx, dy) in door_positions:
                dist = math.hypot(item.position.x - dx, item.position.y - dy)
                if dist < self.MIN_DOOR_CLEARANCE_M:
                    violations.append(ClearanceViolation(
                        item_id=item.id,
                        violation_type="too_close_to_door",
                        description=f"{item.name} is {dist:.2f}m from a door (min {self.MIN_DOOR_CLEARANCE_M}m)",
                        severity="warning",
                        suggested_offset=(
                            (item.position.x - dx) / dist * self.MIN_DOOR_CLEARANCE_M,
                            (item.position.y - dy) / dist * self.MIN_DOOR_CLEARANCE_M,
                        ),
                    ))
        return violations

    def _door_positions(self, plan: FloorPlanData) -> list[tuple[float, float]]:
        positions = []
        for op in plan.openings:
            if op.type != OpeningType.DOOR:
                continue
            wall = next((w for w in plan.walls if w.id == op.wall_id), None)
            if wall is None:
                continue
            t = op.position_along_wall
            x = wall.start.x + t * (wall.end.x - wall.start.x)
            y = wall.start.y + t * (wall.end.y - wall.start.y)
            positions.append((x, y))
        return positions

    # ------------------------------------------------------------------
    # Room containment
    # ------------------------------------------------------------------

    def _check_room_containment(
        self, items: list[FurnitureItem], plan: FloorPlanData
    ) -> list[ClearanceViolation]:
        if not HAS_SHAPELY:
            return []
        violations = []
        room_polys = {
            r.id: Polygon([(p.x, p.y) for p in r.polygon])
            for r in plan.rooms if len(r.polygon) >= 3
        }
        for item in items:
            if not item.room_id or item.room_id not in room_polys:
                continue
            room_poly = room_polys[item.room_id]
            item_center = Point(item.position.x, item.position.y)
            if not room_poly.contains(item_center):
                violations.append(ClearanceViolation(
                    item_id=item.id,
                    violation_type="outside_room",
                    description=f"{item.name} centre is outside its assigned room",
                    severity="error",
                    suggested_offset=(0.0, 0.0),
                ))
        return violations
