"""Pydantic request/response models for the FastAPI API."""

from __future__ import annotations
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class StyleEnum(str, Enum):
    modern_organic = "modern_organic"
    japandi = "japandi"
    scandinavian = "scandinavian"
    contemporary_luxury = "contemporary_luxury"
    minimalist = "minimalist"
    transitional = "transitional"
    mid_century_modern = "mid_century_modern"


class RenderModeEnum(str, Enum):
    preview = "preview"
    photoreal = "photoreal"
    topdown = "topdown"
    walkthrough = "walkthrough"
    material_board = "material_board"


# ── Request models ──────────────────────────────────────────────────────────

class DesignRequest(BaseModel):
    session_id: Optional[str] = None
    style: StyleEnum = StyleEnum.modern_organic
    prompt: str = Field(default="", description="Natural language design description")
    priority_rooms: list[str] = Field(default_factory=list)
    family_friendly: bool = True
    extra_storage: bool = False

    class Config:
        use_enum_values = True


class RenderRequest(BaseModel):
    session_id: str
    mode: RenderModeEnum = RenderModeEnum.preview
    resolution_w: int = 1920
    resolution_h: int = 1080
    samples: int = 64
    camera_preset: Optional[str] = None  # "eye_level", "three_quarter", "top_down"

    class Config:
        use_enum_values = True


class EditRequest(BaseModel):
    session_id: str
    command: str = Field(..., description="Natural language edit command")


class PaletteRequest(BaseModel):
    hex_colors: list[str] = Field(..., min_length=1, max_length=10)


# ── Response models ─────────────────────────────────────────────────────────

class SessionResponse(BaseModel):
    session_id: str
    status: str
    message: str


class DesignResponse(BaseModel):
    session_id: str
    style: str
    room_count: int
    furniture_count: int
    violations: list[str] = Field(default_factory=list)
    preview_url: Optional[str] = None


class RenderJobResponse(BaseModel):
    job_id: str
    session_id: str
    mode: str
    status: str
    output_url: Optional[str] = None
    error: Optional[str] = None
    duration_s: Optional[float] = None


class EditResponse(BaseModel):
    session_id: str
    command: str
    intent_type: str
    intent_confidence: float
    description: str
    furniture_count: int
    violations: list[str] = Field(default_factory=list)


class IntentPreviewResponse(BaseModel):
    command: str
    intent_type: str
    confidence: float
    description: str


class AssetListResponse(BaseModel):
    assets: list[dict]
    total: int


class StyleListResponse(BaseModel):
    styles: list[dict]


class HealthResponse(BaseModel):
    status: str
    blender_available: bool
    version: str = "0.1.0"
