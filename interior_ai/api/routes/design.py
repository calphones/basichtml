"""Design generation and session management endpoints."""

from __future__ import annotations
from fastapi import APIRouter, HTTPException, Request
from typing import Optional

from ..models import (
    DesignRequest, DesignResponse,
    SessionResponse, StyleListResponse,
)
from ...types import DesignSpec, DesignStyle, RoomType
from ...design_engine.style_profiles import STYLE_PROFILES

router = APIRouter(prefix="/design", tags=["design"])


@router.post("/generate", response_model=DesignResponse)
async def generate_design(req: DesignRequest, request: Request):
    """Generate a complete interior design from uploaded floor plans."""
    session_mgr = request.app.state.session_manager
    session = session_mgr.get_or_create(req.session_id)

    if session.floor_plan is None:
        raise HTTPException(
            400,
            "No floor plan loaded for this session. Upload a floor plan first."
        )

    spec = DesignSpec(
        style=DesignStyle(req.style),
        priority_rooms=[RoomType(r) for r in req.priority_rooms if r in RoomType._value2member_map_],
        natural_language_prompt=req.prompt,
        family_friendly=req.family_friendly,
        extra_storage=req.extra_storage,
    )
    session.spec = spec

    # Run the design pipeline
    from ...reconstruction.room_reconstructor import RoomReconstructor
    from ...design_engine.furniture_placer import FurniturePlacer
    from ...design_engine.layout_optimizer import LayoutOptimizer
    from ...design_engine.clearance_checker import ClearanceChecker
    from ...blender_integration.scene_builder import BlenderSceneBuilder
    from ...blender_integration.material_applier import BlenderMaterialApplier

    try:
        reconstructor = RoomReconstructor()
        scene = reconstructor.reconstruct(session.floor_plan, spec=spec)

        placer = FurniturePlacer(spec)
        scene = placer.place_for_scene(scene)

        optimizer = LayoutOptimizer()
        scene = optimizer.optimize(scene)

        builder = BlenderSceneBuilder()
        scene = builder.prepare(scene, spec)

        applier = BlenderMaterialApplier()
        scene = applier.apply(scene)

        checker = ClearanceChecker()
        violations = checker.check_scene(scene)

        session.scene = scene
        session.touch()

        return DesignResponse(
            session_id=session.id,
            style=req.style,
            room_count=len(session.floor_plan.rooms),
            furniture_count=len(scene.furniture),
            violations=[v.description for v in violations if v.severity == "error"],
        )
    except Exception as e:
        raise HTTPException(500, f"Design generation failed: {e}") from e


@router.get("/styles", response_model=StyleListResponse)
async def list_styles():
    """Return all available design styles with descriptions and palettes."""
    styles = []
    for style, profile in STYLE_PROFILES.items():
        styles.append({
            "id": style.value,
            "description": profile.description,
            "wall_color": profile.wall_color_hex,
            "floor_finish": profile.floor_finish,
            "metal_finish": profile.metal_finish,
            "palette": {
                "primary": profile.palette.primary.to_hex(),
                "secondary": profile.palette.secondary.to_hex(),
                "accent": profile.palette.accent.to_hex(),
                "neutral": profile.palette.neutral.to_hex(),
            } if profile.palette else {},
            "keywords": profile.keywords,
        })
    return StyleListResponse(styles=styles)


@router.get("/session/{session_id}")
async def get_session(session_id: str, request: Request):
    """Return current session state."""
    session_mgr = request.app.state.session_manager
    session = session_mgr.get(session_id)
    if session is None:
        raise HTTPException(404, "Session not found or expired")
    return {
        "session_id": session.id,
        "has_floor_plan": session.floor_plan is not None,
        "has_scene": session.scene is not None,
        "furniture_count": len(session.scene.furniture) if session.scene else 0,
        "style": session.scene.style.value if session.scene and session.scene.style else None,
        "command_history": session.command_history[-10:],
    }


@router.delete("/session/{session_id}")
async def delete_session(session_id: str, request: Request):
    """Delete a session and free its resources."""
    session_mgr = request.app.state.session_manager
    deleted = session_mgr.delete(session_id)
    return {"status": "deleted" if deleted else "not_found", "session_id": session_id}


@router.post("/parse-floor-plan")
async def parse_floor_plan(session_id: str, file_path: str, request: Request):
    """Parse a previously uploaded floor plan and attach it to the session."""
    from pathlib import Path
    session_mgr = request.app.state.session_manager
    session = session_mgr.get_or_create(session_id or None)

    fp = Path(file_path)
    if not fp.exists():
        raise HTTPException(404, f"File not found: {file_path}")

    try:
        floor_plan = _parse_file(fp)
        session.floor_plan = floor_plan
        session.touch()
        return {
            "session_id": session.id,
            "rooms_detected": len(floor_plan.rooms),
            "walls_detected": len(floor_plan.walls),
            "stairs_detected": len(floor_plan.stairs),
            "scale_m_per_px": floor_plan.scale_m_per_px,
        }
    except Exception as e:
        raise HTTPException(500, f"Floor plan parsing failed: {e}") from e


def _parse_file(fp):
    ext = fp.suffix.lower()
    if ext == ".pdf":
        from ...input_parser.pdf_parser import PDFParser
        from ...floorplan.detector import FloorPlanDetector
        from ...floorplan.vectorizer import Vectorizer
        from ...floorplan.scale_inferrer import ScaleInferrer
        import numpy as np

        pdf_parser = PDFParser()
        pages = pdf_parser.extract_floor_plans(fp)
        if not pages:
            pages = pdf_parser.extract_pages(fp)
        if not pages:
            from ...types import FloorPlanData
            return FloorPlanData(source_image_path=str(fp))

        image = pages[0]
        scale_inferrer = ScaleInferrer()
        texts = pdf_parser.extract_text(fp)
        scale = scale_inferrer.infer(image, texts)

        detector = FloorPlanDetector(scale_m_per_px=scale)
        result = detector.detect(image)

        from ...types import FloorPlanData
        plan = FloorPlanData(
            walls=result.walls,
            openings=result.openings,
            stairs=result.stairs,
            scale_m_per_px=scale,
            source_image_path=str(fp),
        )
        vectorizer = Vectorizer()
        plan = vectorizer.vectorize(plan)
        return plan

    elif ext in (".dxf",):
        from ...input_parser.dxf_parser import DXFParser
        return DXFParser().parse(fp)

    elif ext in (".ifc",):
        from ...input_parser.ifc_parser import IFCParser
        return IFCParser().parse(fp)

    else:
        from ...input_parser.image_parser import ImageParser
        from ...floorplan.detector import FloorPlanDetector
        from ...floorplan.vectorizer import Vectorizer
        from ...floorplan.scale_inferrer import ScaleInferrer

        img_parser = ImageParser()
        image = img_parser.load(fp)
        preprocessed = img_parser.preprocess_floor_plan(image)
        scale = ScaleInferrer().infer(image)
        detector = FloorPlanDetector(scale_m_per_px=scale)
        result = detector.detect(preprocessed)
        from ...types import FloorPlanData
        plan = FloorPlanData(
            walls=result.walls,
            openings=result.openings,
            stairs=result.stairs,
            scale_m_per_px=scale,
            source_image_path=str(fp),
        )
        return Vectorizer().vectorize(plan)
