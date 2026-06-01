"""Utilities for building and mutating SceneGraph instances."""

from __future__ import annotations
import copy
import json
from pathlib import Path

from ..types import (
    SceneGraph, FurnitureItem, LightSource, Material, Vec3,
    DesignStyle, FloorPlanData
)


class SceneGraphBuilder:
    """Fluent builder for constructing SceneGraph objects."""

    def __init__(self):
        self._scene = SceneGraph()

    def with_floor_plan(self, plan: FloorPlanData) -> "SceneGraphBuilder":
        self._scene.floor_plan = plan
        return self

    def with_style(self, style: DesignStyle) -> "SceneGraphBuilder":
        self._scene.style = style
        return self

    def add_furniture(self, item: FurnitureItem) -> "SceneGraphBuilder":
        self._scene.furniture.append(item)
        return self

    def add_light(self, light: LightSource) -> "SceneGraphBuilder":
        self._scene.lights.append(light)
        return self

    def add_material(self, material: Material) -> "SceneGraphBuilder":
        self._scene.materials[material.name] = material
        return self

    def with_camera(
        self, position: Vec3, target: Vec3, fov: float = 60.0
    ) -> "SceneGraphBuilder":
        self._scene.camera_position = position
        self._scene.camera_target = target
        self._scene.camera_fov = fov
        return self

    def with_hdri(self, path: str) -> "SceneGraphBuilder":
        self._scene.hdri_path = path
        return self

    def build(self) -> SceneGraph:
        return self._scene


class SceneSerializer:
    """Serialise / deserialise SceneGraph to JSON for session persistence."""

    def save(self, scene: SceneGraph, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = self._to_dict(scene)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def load(self, path: str | Path) -> SceneGraph:
        with open(path) as f:
            data = json.load(f)
        return self._from_dict(data)

    # ------------------------------------------------------------------
    # Serialisation helpers (simplified — full round-trip via dataclass fields)
    # ------------------------------------------------------------------

    def _to_dict(self, scene: SceneGraph) -> dict:
        return {
            "style": scene.style.value if scene.style else None,
            "camera_position": self._vec3(scene.camera_position),
            "camera_target": self._vec3(scene.camera_target),
            "camera_fov": scene.camera_fov,
            "hdri_path": scene.hdri_path,
            "furniture_count": len(scene.furniture),
            "light_count": len(scene.lights),
            "material_count": len(scene.materials),
            "metadata": {k: str(v) for k, v in scene.metadata.items()
                         if isinstance(v, (str, int, float, bool))},
        }

    def _from_dict(self, data: dict) -> SceneGraph:
        scene = SceneGraph()
        if data.get("style"):
            scene.style = DesignStyle(data["style"])
        if data.get("camera_position"):
            scene.camera_position = Vec3(**data["camera_position"])
        if data.get("camera_target"):
            scene.camera_target = Vec3(**data["camera_target"])
        scene.camera_fov = data.get("camera_fov", 60.0)
        scene.hdri_path = data.get("hdri_path")
        return scene

    def _vec3(self, v) -> dict | None:
        if v is None:
            return None
        return {"x": v.x, "y": v.y, "z": v.z}


class SceneMutator:
    """Apply structural mutations to a SceneGraph (move, replace, relight)."""

    def move_furniture(
        self, scene: SceneGraph, item_id: str, new_pos: Vec3
    ) -> SceneGraph:
        for item in scene.furniture:
            if item.id == item_id:
                item.position = new_pos
                break
        return scene

    def remove_furniture(self, scene: SceneGraph, item_id: str) -> SceneGraph:
        scene.furniture = [f for f in scene.furniture if f.id != item_id]
        return scene

    def set_light_intensity(
        self, scene: SceneGraph, light_id: str, intensity: float
    ) -> SceneGraph:
        for light in scene.lights:
            if light.id == light_id:
                light.intensity = intensity
                break
        return scene

    def replace_material(
        self, scene: SceneGraph, old_name: str, new_material: Material
    ) -> SceneGraph:
        if old_name in scene.materials:
            scene.materials[old_name] = new_material
        for item in scene.furniture:
            if item.material and item.material.name == old_name:
                item.material = new_material
        return scene

    def clone(self, scene: SceneGraph) -> SceneGraph:
        return copy.deepcopy(scene)
