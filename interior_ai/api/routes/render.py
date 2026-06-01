"""Render endpoint: submit render jobs and retrieve results."""

from __future__ import annotations
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from ..models import RenderRequest, RenderJobResponse, RenderModeEnum
from ...types import RenderMode

router = APIRouter(prefix="/render", tags=["render"])


@router.post("/submit", response_model=RenderJobResponse)
async def submit_render(req: RenderRequest, request: Request):
    """Queue a render job. Returns immediately with job_id for polling."""
    session_mgr = request.app.state.session_manager
    render_mgr = request.app.state.render_manager

    session = session_mgr.get(req.session_id)
    if session is None:
        raise HTTPException(404, "Session not found or expired")
    if session.scene is None:
        raise HTTPException(400, "No design generated yet. Run /design/generate first.")

    mode = RenderMode(req.mode)
    from ...blender_integration.camera_controller import CameraController
    cam_ctrl = CameraController()

    cam_pos = cam_target = None
    if req.camera_preset and session.floor_plan and session.floor_plan.rooms:
        room = session.floor_plan.rooms[0]
        if req.camera_preset == "eye_level":
            cam_pos, cam_target = cam_ctrl.eye_level(room)
        elif req.camera_preset == "three_quarter":
            cam_pos, cam_target = cam_ctrl.three_quarter(room)
        elif req.camera_preset == "top_down":
            cam_pos, cam_target = cam_ctrl.top_down(session.floor_plan)

    job_id = render_mgr.submit(
        scene=session.scene,
        mode=mode,
        resolution=(req.resolution_w, req.resolution_h),
        camera_position=cam_pos,
        camera_target=cam_target,
    )
    session.render_history.append(job_id)
    session.touch()

    return RenderJobResponse(
        job_id=job_id,
        session_id=req.session_id,
        mode=req.mode,
        status="queued",
    )


@router.post("/run/{job_id}", response_model=RenderJobResponse)
async def run_render(job_id: str, request: Request):
    """Execute a queued render job synchronously (blocks until complete)."""
    render_mgr = request.app.state.render_manager
    job = render_mgr.get_job(job_id)
    if job is None:
        raise HTTPException(404, "Render job not found")
    if not request.app.state.blender_bridge.is_available():
        raise HTTPException(503, "Blender is not available. Install Blender and set BLENDER_PATH.")
    try:
        job = render_mgr.run_sync(job_id)
        duration = (job.finished_at - job.started_at) if job.finished_at and job.started_at else None
        output_url = f"/render/result/{job_id}" if job.output_path else None
        return RenderJobResponse(
            job_id=job_id,
            session_id="",
            mode=job.request.mode.value,
            status=job.status.value,
            output_url=output_url,
            error=job.error,
            duration_s=round(duration, 1) if duration else None,
        )
    except Exception as e:
        raise HTTPException(500, f"Render failed: {e}") from e


@router.get("/status/{job_id}", response_model=RenderJobResponse)
async def render_status(job_id: str, request: Request):
    """Check the status of a render job."""
    render_mgr = request.app.state.render_manager
    job = render_mgr.get_job(job_id)
    if job is None:
        raise HTTPException(404, "Render job not found")
    output_url = f"/render/result/{job_id}" if job.output_path else None
    duration = (job.finished_at - job.started_at) if job.finished_at and job.started_at else None
    return RenderJobResponse(
        job_id=job_id,
        session_id="",
        mode=job.request.mode.value,
        status=job.status.value,
        output_url=output_url,
        error=job.error,
        duration_s=round(duration, 1) if duration else None,
    )


@router.get("/result/{job_id}")
async def get_render_result(job_id: str, request: Request):
    """Download the rendered image for a completed job."""
    render_mgr = request.app.state.render_manager
    job = render_mgr.get_job(job_id)
    if job is None:
        raise HTTPException(404, "Render job not found")
    if job.output_path is None or not job.output_path.exists():
        raise HTTPException(404, "Render output not available")
    return FileResponse(
        path=str(job.output_path),
        media_type="image/png",
        filename=f"render_{job_id}.png",
    )
