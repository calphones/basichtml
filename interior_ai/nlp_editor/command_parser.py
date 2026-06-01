"""Parse and resolve NLP commands against the current scene state."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

from ..types import (
    SceneGraph, FurnitureItem, FurnitureCategory,
    DesignStyle, Vec3, LightSource
)
from .intent_classifier import IntentClassifier, Intent, IntentType


@dataclass
class ParsedCommand:
    intent: Intent
    target_item: Optional[FurnitureItem] = None
    new_position: Optional[Vec3] = None
    new_style: Optional[DesignStyle] = None
    new_category: Optional[FurnitureCategory] = None
    brightness_delta: float = 0.0    # +/- multiplier on light intensity
    notes: str = ""


class CommandParser:
    """Resolve NLP intents into concrete scene mutations.

    Takes a classified Intent and the current SceneGraph, and produces
    a ParsedCommand with specific objects and values resolved from the scene.
    """

    DIRECTION_TO_OFFSET: dict[str, tuple[float, float]] = {
        "closer": (0, 0.5),
        "further": (0, -0.5),
        "left": (-0.5, 0),
        "right": (0.5, 0),
        "center": None,
    }

    def __init__(self):
        self._classifier = IntentClassifier()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse(self, text: str, scene: SceneGraph) -> ParsedCommand:
        intent = self._classifier.classify(text)
        return self._resolve(intent, scene)

    # ------------------------------------------------------------------
    # Resolution
    # ------------------------------------------------------------------

    def _resolve(self, intent: Intent, scene: SceneGraph) -> ParsedCommand:
        cmd = ParsedCommand(intent=intent)

        if intent.type == IntentType.MOVE_FURNITURE:
            cmd.target_item = self._find_furniture(scene, intent.subject or "")
            if cmd.target_item and intent.target:
                cmd.new_position = self._resolve_position(
                    cmd.target_item.position, intent.target, scene
                )

        elif intent.type == IntentType.REPLACE_FURNITURE:
            cmd.target_item = self._find_furniture(scene, intent.subject or "")
            cmd.new_category = self._resolve_category(intent.target or "")

        elif intent.type == IntentType.REMOVE_FURNITURE:
            cmd.target_item = self._find_furniture(scene, intent.subject or "")

        elif intent.type == IntentType.ADD_FURNITURE:
            cmd.new_category = self._resolve_category(intent.subject or "")

        elif intent.type == IntentType.CHANGE_STYLE:
            style_str = (intent.subject or "").lower().replace(" ", "_")
            try:
                cmd.new_style = DesignStyle(style_str)
            except ValueError:
                cmd.new_style = self._fuzzy_style(style_str)

        elif intent.type in (IntentType.CHANGE_BRIGHTNESS, IntentType.CHANGE_LIGHTING):
            cmd.brightness_delta = self._resolve_brightness(
                intent.subject or intent.modifier or ""
            )

        elif intent.type == IntentType.ADD_STORAGE:
            cmd.new_category = FurnitureCategory.STORAGE
            cmd.notes = "Additional storage requested"

        elif intent.type == IntentType.MAKE_FAMILY_FRIENDLY:
            cmd.notes = "family_friendly"

        return cmd

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _find_furniture(self, scene: SceneGraph, subject: str) -> Optional[FurnitureItem]:
        subject_lower = subject.lower().strip()
        if not subject_lower:
            return None
        # Exact name match first
        for item in scene.furniture:
            if subject_lower in item.name.lower():
                return item
        # Category match
        for item in scene.furniture:
            if subject_lower in item.category.value:
                return item
        return None

    def _resolve_position(
        self, current: Vec3, target_text: str, scene: SceneGraph
    ) -> Vec3:
        text = target_text.lower()
        # Named reference points
        if "fireplace" in text:
            return Vec3(current.x + 1.0, current.y, current.z)
        if "window" in text:
            return Vec3(current.x, current.y + 1.5, current.z)
        if "center" in text or "centre" in text:
            if scene.floor_plan and scene.floor_plan.rooms:
                c = scene.floor_plan.rooms[0].centroid
                return Vec3(c.x, c.y, current.z)
        # Direction words
        for word, offset in self.DIRECTION_TO_OFFSET.items():
            if word in text and offset is not None:
                return Vec3(current.x + offset[0], current.y + offset[1], current.z)
        return current

    def _resolve_category(self, text: str) -> Optional[FurnitureCategory]:
        text = text.lower()
        mapping = {
            "sofa": FurnitureCategory.SEATING,
            "couch": FurnitureCategory.SEATING,
            "sectional": FurnitureCategory.SECTIONAL,
            "chair": FurnitureCategory.ACCENT_CHAIR,
            "coffee table": FurnitureCategory.COFFEE_TABLE,
            "rug": FurnitureCategory.RUG,
            "lamp": FurnitureCategory.LAMP,
            "storage": FurnitureCategory.STORAGE,
            "shelf": FurnitureCategory.BOOKSHELF,
            "bookshelf": FurnitureCategory.BOOKSHELF,
            "tv": FurnitureCategory.TV_UNIT,
            "bed": FurnitureCategory.BED,
        }
        for key, cat in mapping.items():
            if key in text:
                return cat
        return None

    def _resolve_brightness(self, text: str) -> float:
        text = text.lower()
        if any(w in text for w in ["brighter", "more light", "more brightness", "lighter"]):
            return 0.5
        if any(w in text for w in ["dimmer", "darker", "softer", "less light"]):
            return -0.4
        if "warm" in text:
            return 0.1
        if "dramatic" in text:
            return 0.3
        return 0.0

    def _fuzzy_style(self, text: str) -> Optional[DesignStyle]:
        mappings = {
            "organic": DesignStyle.MODERN_ORGANIC,
            "zen": DesignStyle.JAPANDI,
            "nordic": DesignStyle.SCANDINAVIAN,
            "luxury": DesignStyle.CONTEMPORARY_LUXURY,
            "clean": DesignStyle.MINIMALIST,
            "classic": DesignStyle.TRANSITIONAL,
            "retro": DesignStyle.MID_CENTURY_MODERN,
            "mcm": DesignStyle.MID_CENTURY_MODERN,
        }
        for key, style in mappings.items():
            if key in text:
                return style
        return DesignStyle.MODERN_ORGANIC
