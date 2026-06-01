"""Build and query a spatial adjacency graph of rooms."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

try:
    import networkx as nx
    HAS_NX = True
except ImportError:
    HAS_NX = False

try:
    from shapely.geometry import Polygon, LineString
    HAS_SHAPELY = True
except ImportError:
    HAS_SHAPELY = False

from ..types import Room, WallSegment, Opening, OpeningType, FloorPlanData


@dataclass
class RoomEdge:
    room_a: str
    room_b: str
    shared_wall_id: str
    opening_type: Optional[OpeningType] = None
    opening_width: float = 0.0


class RoomGraph:
    """Directed graph of room adjacencies.

    Nodes = rooms (by id).
    Edges = shared walls with optional door/window openings.

    Used by the design engine to determine traffic flow, view corridors,
    and which rooms should be visually connected.
    """

    def __init__(self):
        if not HAS_NX:
            raise ImportError("networkx is required: pip install networkx")
        self._graph = nx.Graph()

    # ------------------------------------------------------------------
    # Building the graph
    # ------------------------------------------------------------------

    def build(self, floor_plan: FloorPlanData) -> "RoomGraph":
        self._graph.clear()
        for room in floor_plan.rooms:
            self._graph.add_node(room.id, room=room)
        self._add_adjacencies(floor_plan)
        return self

    def _add_adjacencies(self, floor_plan: FloorPlanData) -> None:
        if not HAS_SHAPELY:
            return
        polys: dict[str, Polygon] = {}
        for room in floor_plan.rooms:
            coords = [(p.x, p.y) for p in room.polygon]
            if len(coords) >= 3:
                polys[room.id] = Polygon(coords)

        room_ids = list(polys.keys())
        opening_wall_ids = {op.wall_id: op for op in floor_plan.openings}

        for i in range(len(room_ids)):
            for j in range(i + 1, len(room_ids)):
                rid_a, rid_b = room_ids[i], room_ids[j]
                pa, pb = polys[rid_a], polys[rid_b]
                if pa.touches(pb) or pa.intersects(pb.buffer(0.1)):
                    shared = self._find_shared_wall(rid_a, rid_b, floor_plan)
                    opening = None
                    opening_width = 0.0
                    if shared and shared.id in opening_wall_ids:
                        op = opening_wall_ids[shared.id]
                        opening = op.type
                        opening_width = op.width
                    self._graph.add_edge(
                        rid_a, rid_b,
                        shared_wall=shared.id if shared else None,
                        opening_type=opening,
                        opening_width=opening_width,
                    )

    def _find_shared_wall(
        self,
        rid_a: str,
        rid_b: str,
        floor_plan: FloorPlanData,
    ) -> Optional[WallSegment]:
        if not HAS_SHAPELY:
            return None
        poly_a = Polygon([(p.x, p.y) for p in next(r for r in floor_plan.rooms if r.id == rid_a).polygon])
        poly_b = Polygon([(p.x, p.y) for p in next(r for r in floor_plan.rooms if r.id == rid_b).polygon])
        for wall in floor_plan.walls:
            line = LineString([(wall.start.x, wall.start.y), (wall.end.x, wall.end.y)])
            if line.distance(poly_a) < 0.3 and line.distance(poly_b) < 0.3:
                return wall
        return None

    # ------------------------------------------------------------------
    # Query API
    # ------------------------------------------------------------------

    def adjacent_rooms(self, room_id: str) -> list[str]:
        """Return ids of rooms directly adjacent to the given room."""
        return list(self._graph.neighbors(room_id))

    def rooms_with_door_access(self, room_id: str) -> list[str]:
        """Return adjacent rooms reachable via a door opening."""
        result = []
        for nb in self._graph.neighbors(room_id):
            data = self._graph.edges[room_id, nb]
            if data.get("opening_type") == OpeningType.DOOR:
                result.append(nb)
        return result

    def traffic_flow_path(self, start_id: str, end_id: str) -> list[str]:
        """Return shortest room-to-room path through door openings."""
        try:
            path = nx.shortest_path(self._graph, start_id, end_id)
            return path
        except nx.NetworkXNoPath:
            return []

    def get_graph(self):
        return self._graph
