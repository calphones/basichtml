"""Classify natural language design commands into structured intents."""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class IntentType(str, Enum):
    MOVE_FURNITURE      = "move_furniture"
    REPLACE_FURNITURE   = "replace_furniture"
    REMOVE_FURNITURE    = "remove_furniture"
    ADD_FURNITURE       = "add_furniture"
    CHANGE_STYLE        = "change_style"
    CHANGE_COLOR        = "change_color"
    CHANGE_MATERIAL     = "change_material"
    CHANGE_LIGHTING     = "change_lighting"
    CHANGE_BRIGHTNESS   = "change_brightness"
    CHANGE_CAMERA       = "change_camera"
    ADD_STORAGE         = "add_storage"
    MAKE_FAMILY_FRIENDLY = "make_family_friendly"
    GENERATE_DESIGN     = "generate_design"
    UNKNOWN             = "unknown"


@dataclass
class Intent:
    type: IntentType
    confidence: float
    subject: Optional[str] = None         # e.g. "sofa", "lighting", "flooring"
    target: Optional[str] = None          # e.g. "closer to fireplace", "lighter"
    modifier: Optional[str] = None        # e.g. "warm", "curved", "dark"
    quantity: Optional[float] = None      # e.g. 0.5 (50% brighter)
    raw_text: str = ""
    entities: dict = field(default_factory=dict)


# Pattern rules: each tuple is (regex, IntentType, subject_group, target_group)
INTENT_RULES: list[tuple] = [

    # Movement
    (r"move\s+(?:the\s+)?(\w[\w\s]+?)\s+(?:closer\s+to|towards?|near|away\s+from|to)\s+([\w\s]+)",
     IntentType.MOVE_FURNITURE, 1, 2),

    # Replacement
    (r"replace\s+(?:the\s+)?(\w[\w\s]+?)\s+with\s+([\w\s]+)",
     IntentType.REPLACE_FURNITURE, 1, 2),

    (r"swap\s+(?:the\s+)?(\w[\w\s]+?)\s+for\s+([\w\s]+)",
     IntentType.REPLACE_FURNITURE, 1, 2),

    # Removal
    (r"remove\s+(?:the\s+)?(\w[\w\s]+)",
     IntentType.REMOVE_FURNITURE, 1, None),

    (r"take\s+(?:out|away)\s+(?:the\s+)?(\w[\w\s]+)",
     IntentType.REMOVE_FURNITURE, 1, None),

    # Addition
    (r"add\s+(?:a\s+|an\s+|more\s+)?(\w[\w\s]+)",
     IntentType.ADD_FURNITURE, 1, None),

    # Style
    (r"(?:make|change)\s+(?:it|the room|style)\s+(?:more\s+)?([\w\s]+?)\s+(?:style|aesthetic|look)",
     IntentType.CHANGE_STYLE, 1, None),

    (r"(?:use|apply|go with)\s+(?:a\s+)?(japandi|scandinavian|minimalist|organic|luxury|transitional|mid.century)\s+(?:style|aesthetic|look)?",
     IntentType.CHANGE_STYLE, 1, None),

    # Colour
    (r"(?:use|make|change to|paint)\s+(?:it\s+)?(?:the\s+)?(\w+\s+)?(?:color|colour|paint|wall)\s+([\w\s]+)",
     IntentType.CHANGE_COLOR, 2, None),

    (r"(?:lighter|darker|warmer|cooler)\s+(\w+)",
     IntentType.CHANGE_COLOR, 1, None),

    # Material
    (r"(?:use|add|apply)\s+([\w\s]+?)\s+(?:wood|marble|stone|leather|linen|boucle|velvet|fabric|finish|flooring|floor)",
     IntentType.CHANGE_MATERIAL, 1, None),

    # Lighting
    (r"(?:make|turn)\s+(?:the\s+)?(?:room\s+)?(?:lights?\s+)?(brighter|dimmer|warmer|cooler|softer|more dramatic)",
     IntentType.CHANGE_BRIGHTNESS, 1, None),

    (r"(?:add|use)\s+(warm|soft|bright|dramatic|cozy|cool|natural)\s+lighting",
     IntentType.CHANGE_LIGHTING, 1, None),

    (r"more\s+(light|brightness|warmth|drama)",
     IntentType.CHANGE_BRIGHTNESS, 1, None),

    # Camera
    (r"(?:show|view|look)\s+(?:from|at)\s+([\w\s]+)",
     IntentType.CHANGE_CAMERA, 1, None),

    # Storage
    (r"(?:add|need|want)\s+more\s+storage",
     IntentType.ADD_STORAGE, None, None),

    # Family-friendly
    (r"(?:family.friendly|kid.friendly|child.friendly|safer\s+for\s+kids?)",
     IntentType.MAKE_FAMILY_FRIENDLY, None, None),
]


class IntentClassifier:
    """Rule-based intent classifier for interior design natural language commands."""

    def classify(self, text: str) -> Intent:
        text_clean = text.strip().lower()
        for pattern, intent_type, subj_group, tgt_group in INTENT_RULES:
            m = re.search(pattern, text_clean, re.IGNORECASE)
            if m:
                subject = m.group(subj_group).strip() if subj_group and len(m.groups()) >= subj_group else None
                target = m.group(tgt_group).strip() if tgt_group and len(m.groups()) >= tgt_group else None
                modifier = self._extract_modifier(text_clean)
                return Intent(
                    type=intent_type,
                    confidence=0.85,
                    subject=subject,
                    target=target,
                    modifier=modifier,
                    raw_text=text,
                    entities=self._extract_entities(text_clean),
                )
        # No rule matched
        return Intent(
            type=IntentType.UNKNOWN,
            confidence=0.1,
            raw_text=text,
        )

    def classify_batch(self, texts: list[str]) -> list[Intent]:
        return [self.classify(t) for t in texts]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _extract_modifier(self, text: str) -> Optional[str]:
        modifiers = [
            "lighter", "darker", "warmer", "cooler", "curved", "straight",
            "smaller", "larger", "natural", "modern", "traditional", "minimal",
            "cozy", "airy", "bright", "dramatic",
        ]
        for mod in modifiers:
            if mod in text:
                return mod
        return None

    def _extract_entities(self, text: str) -> dict:
        entities = {}
        furniture_words = [
            "sofa", "sectional", "couch", "chair", "table", "coffee table",
            "dining table", "bed", "nightstand", "rug", "lamp", "bookshelf",
            "tv unit", "cabinet", "desk",
        ]
        color_words = [
            "white", "black", "grey", "gray", "beige", "cream", "brown",
            "navy", "green", "blue", "oak", "walnut",
        ]
        direction_words = [
            "left", "right", "forward", "back", "center", "fireplace",
            "window", "door", "wall",
        ]
        for f in furniture_words:
            if f in text:
                entities.setdefault("furniture", []).append(f)
        for c in color_words:
            if c in text:
                entities.setdefault("colors", []).append(c)
        for d in direction_words:
            if d in text:
                entities.setdefault("directions", []).append(d)
        return entities
