"""Predefined lighting setups per design mood."""

from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class LightingProfile:
    name: str
    description: str
    color_temp_k: int
    ambient_intensity: float
    accent_intensity: float
    use_indirect: bool
    hdri_id: str
    time_of_day: str
    keywords: list[str] = field(default_factory=list)


LIGHT_PROFILES: dict[str, LightingProfile] = {

    "cozy_evening": LightingProfile(
        name="cozy_evening",
        description="Warm amber tones, soft shadows, intimate scale",
        color_temp_k=2400,
        ambient_intensity=1.5,
        accent_intensity=2.0,
        use_indirect=True,
        hdri_id="indoor_warm",
        time_of_day="evening",
        keywords=["cozy", "warm", "intimate", "evening", "amber", "soft"],
    ),

    "bright_airy": LightingProfile(
        name="bright_airy",
        description="Clean white daylight, Scandinavian freshness",
        color_temp_k=5000,
        ambient_intensity=3.5,
        accent_intensity=1.0,
        use_indirect=False,
        hdri_id="overcast_sky",
        time_of_day="midday",
        keywords=["bright", "airy", "fresh", "clean", "daylight", "white", "nordic"],
    ),

    "golden_hour": LightingProfile(
        name="golden_hour",
        description="Dramatic warm directional light, long shadows",
        color_temp_k=3000,
        ambient_intensity=2.0,
        accent_intensity=3.0,
        use_indirect=True,
        hdri_id="venice_sunset",
        time_of_day="golden_hour",
        keywords=["golden", "dramatic", "sunset", "warm", "moody"],
    ),

    "modern_neutral": LightingProfile(
        name="modern_neutral",
        description="Studio-quality neutral light for accurate material display",
        color_temp_k=5500,
        ambient_intensity=3.0,
        accent_intensity=1.5,
        use_indirect=False,
        hdri_id="studio_small",
        time_of_day="midday",
        keywords=["neutral", "studio", "clean", "professional", "accurate"],
    ),

    "luxury_evening": LightingProfile(
        name="luxury_evening",
        description="Deep shadows, spot accents, dramatic luxury ambience",
        color_temp_k=2700,
        ambient_intensity=1.0,
        accent_intensity=4.0,
        use_indirect=True,
        hdri_id="indoor_warm",
        time_of_day="evening",
        keywords=["luxury", "dramatic", "dark", "moody", "evening", "spot"],
    ),
}
