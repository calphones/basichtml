"""Manage HDRI environment maps for Blender Cycles rendering."""

from __future__ import annotations
import json
from pathlib import Path
from typing import Optional


BUILT_IN_HDRI_CATALOG = [
    {"id": "venice_sunset", "file": "venice_sunset_4k.hdr",
     "description": "Golden hour, warm directional light from west",
     "color_temp_k": 3200, "tags": ["warm", "golden", "sunset", "dramatic"]},
    {"id": "studio_small", "file": "studio_small_08_4k.hdr",
     "description": "Soft diffuse studio lighting, neutral white",
     "color_temp_k": 5500, "tags": ["neutral", "studio", "diffuse", "clean"]},
    {"id": "overcast_sky", "file": "overcast_sky_4k.hdr",
     "description": "Even overcast daylight, minimal shadows",
     "color_temp_k": 6500, "tags": ["overcast", "soft", "daylight", "even"]},
    {"id": "morning_light", "file": "morning_light_4k.hdr",
     "description": "Soft cool morning light from the east",
     "color_temp_k": 4500, "tags": ["morning", "cool", "soft", "natural"]},
    {"id": "indoor_warm", "file": "indoor_warm_4k.hdr",
     "description": "Warm interior ambient, evening mood",
     "color_temp_k": 2700, "tags": ["warm", "cozy", "interior", "evening"]},
]


class HDRIManager:
    """Discover, select, and configure HDRI environment maps.

    HDRI files should be placed in assets/hdri/.
    Download CC0 HDRI maps from Poly Haven (https://polyhaven.com/hdris).
    """

    def __init__(self, hdri_dir: str | Path = "./assets/hdri"):
        self._dir = Path(hdri_dir)
        self._catalog = {h["id"]: h for h in BUILT_IN_HDRI_CATALOG}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def resolve(self, hdri_id: str) -> Optional[Path]:
        """Return local path to HDRI file if it exists."""
        info = self._catalog.get(hdri_id)
        if info is None:
            return None
        path = self._dir / info["file"]
        return path if path.exists() else None

    def best_for_style(self, style_name: str) -> str:
        """Return the HDRI id best suited for the given design style."""
        warm_styles = {"modern_organic", "mid_century_modern", "transitional",
                        "contemporary_luxury"}
        cool_styles = {"japandi", "scandinavian", "minimalist"}
        if style_name in warm_styles:
            return "venice_sunset"
        if style_name in cool_styles:
            return "morning_light"
        return "studio_small"

    def best_for_prompt(self, prompt: str) -> str:
        """Match NL prompt words to HDRI catalog tags."""
        prompt_lower = prompt.lower()
        scores = {}
        for hdri_id, info in self._catalog.items():
            score = sum(1 for tag in info["tags"] if tag in prompt_lower)
            scores[hdri_id] = score
        best = max(scores, key=scores.get)
        return best if scores[best] > 0 else "studio_small"

    def available(self) -> list[dict]:
        """Return catalog entries for HDRIs present on disk."""
        result = []
        for info in self._catalog.values():
            path = self._dir / info["file"]
            result.append({**info, "available": path.exists()})
        return result

    def scan_local(self) -> list[str]:
        """Return .hdr/.exr files found in hdri_dir not already in catalog."""
        extra = []
        if not self._dir.exists():
            return extra
        for f in self._dir.iterdir():
            if f.suffix.lower() in {".hdr", ".exr"}:
                hdri_id = f.stem
                if hdri_id not in self._catalog:
                    self._catalog[hdri_id] = {
                        "id": hdri_id, "file": f.name,
                        "description": "User-provided HDRI",
                        "color_temp_k": 5500,
                        "tags": [],
                    }
                    extra.append(hdri_id)
        return extra
