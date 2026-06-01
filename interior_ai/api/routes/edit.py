"""Natural language scene edit endpoints."""

from __future__ import annotations
from fastapi import APIRouter, HTTPException, Request

from ..models import EditRequest, EditResponse, IntentPreviewResponse
from ...design_engine.clearance_checker import ClearanceChecker
from ...nlp_editor.scene_mutator import NLPSceneMutator
from ...nlp_editor.intent_classifier import IntentClassifier

router = APIRouter(prefix="/edit", tags=["edit"])

_mutator = NLPSceneMutator()
_classifier = IntentClassifier()
_checker = ClearanceChecker()


@router.post("/command", response_model=EditResponse)
async def apply_command(req: EditRequest, request: Request):
    """Apply a natural language edit command to the current scene."""
    session_mgr = request.app.state.session_manager
    session = session_mgr.get(req.session_id)
    if session is None:
        raise HTTPException(404, "Session not found or expired")
    if session.scene is None:
        raise HTTPException(400, "No scene to edit. Run /design/generate first.")

    try:
        intent = _classifier.classify(req.command)
        new_scene = _mutator.apply(req.command, session.scene)
        violations = _checker.check_scene(new_scene)
        session.scene = new_scene
        session.command_history.append(req.command)
        session.touch()
        return EditResponse(
            session_id=req.session_id,
            command=req.command,
            intent_type=intent.type.value,
            intent_confidence=intent.confidence,
            description=_mutator.preview_intent(req.command),
            furniture_count=len(new_scene.furniture),
            violations=[v.description for v in violations if v.severity == "error"],
        )
    except Exception as e:
        raise HTTPException(500, f"Edit failed: {e}") from e


@router.post("/preview", response_model=IntentPreviewResponse)
async def preview_intent(command: str):
    """Return what a command would do without applying it."""
    intent = _classifier.classify(command)
    description = _mutator.preview_intent(command)
    return IntentPreviewResponse(
        command=command,
        intent_type=intent.type.value,
        confidence=intent.confidence,
        description=description,
    )


@router.post("/undo/{session_id}")
async def undo(session_id: str, request: Request):
    """Undo the last edit command (regenerates from command history)."""
    session_mgr = request.app.state.session_manager
    session = session_mgr.get(session_id)
    if session is None:
        raise HTTPException(404, "Session not found")
    if not session.command_history:
        return {"status": "nothing_to_undo"}

    session.command_history.pop()

    if session.floor_plan is None:
        return {"status": "cannot_undo_no_floor_plan"}

    from ...reconstruction.room_reconstructor import RoomReconstructor
    from ...design_engine.furniture_placer import FurniturePlacer
    from ...design_engine.layout_optimizer import LayoutOptimizer
    from ...blender_integration.scene_builder import BlenderSceneBuilder
    from ...blender_integration.material_applier import BlenderMaterialApplier

    try:
        reconstructor = RoomReconstructor()
        scene = reconstructor.reconstruct(session.floor_plan, spec=session.spec)
        if session.spec:
            placer = FurniturePlacer(session.spec)
            scene = placer.place_for_scene(scene)
            optimizer = LayoutOptimizer()
            scene = optimizer.optimize(scene)
        builder = BlenderSceneBuilder()
        scene = builder.prepare(scene, session.spec)
        applier = BlenderMaterialApplier()
        scene = applier.apply(scene)

        # Re-apply all remaining commands
        for cmd_text in session.command_history:
            scene = _mutator.apply(cmd_text, scene)

        session.scene = scene
        session.touch()
        return {
            "status": "undone",
            "remaining_commands": len(session.command_history),
            "furniture_count": len(scene.furniture),
        }
    except Exception as e:
        raise HTTPException(500, f"Undo failed: {e}") from e
