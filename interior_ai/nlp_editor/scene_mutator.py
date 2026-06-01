"""Apply parsed NLP commands to a SceneGraph."""

from __future__ import annotations
import copy
import uuid

from ..types import (
    SceneGraph, FurnitureItem, Vec3, DesignStyle,
    FurnitureCategory, LightSource
)
from .command_parser import CommandParser, ParsedCommand
from .intent_classifier import IntentType


class NLPSceneMutator:
    """Apply natural language commands to a SceneGraph, returning a modified copy.

    Each call returns a new SceneGraph (immutable pattern) so callers can
    maintain undo history.
    """

    def __init__(self):
        self._parser = CommandParser()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def apply(self, text: str, scene: SceneGraph) -> SceneGraph:
        """Parse `text` and apply the resulting mutation to `scene`.

        Returns a deep copy of the scene with modifications applied.
        """
        scene = copy.deepcopy(scene)
        cmd = self._parser.parse(text, scene)
        return self._execute(cmd, scene)

    def apply_batch(self, commands: list[str], scene: SceneGraph) -> SceneGraph:
        """Apply multiple commands in sequence."""
        for text in commands:
            scene = self.apply(text, scene)
        return scene

    def preview_intent(self, text: str) -> str:
        """Return a human-readable description of what the command would do."""
        cmd = self._parser.parse(text, SceneGraph())
        return self._describe_command(cmd)

    # ------------------------------------------------------------------
    # Command execution
    # ------------------------------------------------------------------

    def _execute(self, cmd: ParsedCommand, scene: SceneGraph) -> SceneGraph:
        intent_type = cmd.intent.type

        if intent_type == IntentType.MOVE_FURNITURE and cmd.target_item and cmd.new_position:
            for item in scene.furniture:
                if item.id == cmd.target_item.id:
                    item.position = cmd.new_position
                    break

        elif intent_type == IntentType.REMOVE_FURNITURE and cmd.target_item:
            scene.furniture = [f for f in scene.furniture if f.id != cmd.target_item.id]

        elif intent_type == IntentType.REPLACE_FURNITURE and cmd.target_item:
            if cmd.new_category:
                for item in scene.furniture:
                    if item.id == cmd.target_item.id:
                        item.category = cmd.new_category
                        item.name = cmd.new_category.value.replace("_", " ").title()

        elif intent_type == IntentType.ADD_FURNITURE and cmd.new_category:
            new_item = self._create_furniture(cmd.new_category, scene)
            scene.furniture.append(new_item)

        elif intent_type == IntentType.CHANGE_STYLE and cmd.new_style:
            scene.style = cmd.new_style
            # Re-apply materials for new style
            from ..materials.texture_mapper import TextureMapper
            mapper = TextureMapper()
            scene = mapper.apply_style(scene)

        elif intent_type in (IntentType.CHANGE_BRIGHTNESS, IntentType.CHANGE_LIGHTING):
            for light in scene.lights:
                if cmd.brightness_delta > 0:
                    light.intensity = min(light.intensity * (1 + cmd.brightness_delta), 20.0)
                else:
                    light.intensity = max(light.intensity * (1 + cmd.brightness_delta), 0.1)

        elif intent_type == IntentType.ADD_STORAGE:
            storage_item = self._create_furniture(FurnitureCategory.STORAGE, scene)
            scene.furniture.append(storage_item)

        elif intent_type == IntentType.MAKE_FAMILY_FRIENDLY:
            scene = self._make_family_friendly(scene)

        return scene

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _create_furniture(
        self, category: FurnitureCategory, scene: SceneGraph
    ) -> FurnitureItem:
        # Place near room centroid
        pos = Vec3(0, 0, 0)
        if scene.floor_plan and scene.floor_plan.rooms:
            c = scene.floor_plan.rooms[0].centroid
            pos = Vec3(c.x + 1.0, c.y + 1.0, 0.0)
        return FurnitureItem(
            id=f"{category.value}_{uuid.uuid4().hex[:6]}",
            category=category,
            name=category.value.replace("_", " ").title(),
            position=pos,
        )

    def _make_family_friendly(self, scene: SceneGraph) -> SceneGraph:
        # Round corners: remove coffee tables (replace with ottoman), add rugs
        sharp_cats = {FurnitureCategory.COFFEE_TABLE}
        for item in scene.furniture:
            if item.category in sharp_cats:
                item.name = "Round Ottoman (family-safe)"
                item.scale = Vec3(item.scale.x * 0.9, item.scale.y * 0.9, item.scale.z * 0.8)
        # Ensure rug present for cushioned flooring feel
        has_rug = any(f.category == FurnitureCategory.RUG for f in scene.furniture)
        if not has_rug:
            scene.furniture.append(self._create_furniture(FurnitureCategory.RUG, scene))
        return scene

    def _describe_command(self, cmd: ParsedCommand) -> str:
        t = cmd.intent.type
        if t == IntentType.MOVE_FURNITURE:
            return f"Move {cmd.intent.subject} towards {cmd.intent.target}"
        if t == IntentType.REPLACE_FURNITURE:
            return f"Replace {cmd.intent.subject} with {cmd.intent.target}"
        if t == IntentType.REMOVE_FURNITURE:
            return f"Remove {cmd.intent.subject}"
        if t == IntentType.ADD_FURNITURE:
            return f"Add {cmd.intent.subject}"
        if t == IntentType.CHANGE_STYLE:
            return f"Change style to {cmd.new_style}"
        if t in (IntentType.CHANGE_BRIGHTNESS, IntentType.CHANGE_LIGHTING):
            dir_ = "increase" if cmd.brightness_delta >= 0 else "decrease"
            return f"{dir_.capitalize()} lighting ({abs(cmd.brightness_delta)*100:.0f}%)"
        return f"Unknown command ({cmd.intent.raw_text})"
