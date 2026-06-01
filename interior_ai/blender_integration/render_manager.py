"""Manage render jobs: queuing, progress tracking, output handling."""

from __future__ import annotations
import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional, Callable

from ..types import SceneGraph, RenderMode, RenderRequest, Vec3
from .blender_bridge import BlenderBridge


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class RenderJob:
    id: str
    request: RenderRequest
    status: JobStatus = JobStatus.QUEUED
    output_path: Optional[Path] = None
    error: Optional[str] = None
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    progress: float = 0.0
    on_complete: Optional[Callable] = field(default=None, repr=False)


class RenderManager:
    """Manage a queue of Blender render jobs with concurrency control.

    Provides:
    - Job queuing with max parallel renders
    - Fast preview (Eevee, low samples) and final (Cycles, high samples) modes
    - Progress callbacks
    - Output organisation by session/job id
    """

    def __init__(
        self,
        output_root: str | Path = "./output/renders",
        max_parallel: int = 2,
        blender_bridge: Optional[BlenderBridge] = None,
    ):
        self._output_root = Path(output_root)
        self._output_root.mkdir(parents=True, exist_ok=True)
        self._max_parallel = max_parallel
        self._bridge = blender_bridge or BlenderBridge()
        self._jobs: dict[str, RenderJob] = {}
        self._queue: list[str] = []
        self._active: list[str] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def submit(
        self,
        scene: SceneGraph,
        mode: RenderMode = RenderMode.PREVIEW,
        resolution: tuple[int, int] | None = None,
        camera_position: Vec3 | None = None,
        camera_target: Vec3 | None = None,
        on_complete: Optional[Callable] = None,
    ) -> str:
        """Queue a render job and return its job ID."""
        job_id = str(uuid.uuid4())[:8]
        output_path = str(self._output_root / f"{job_id}.png")

        samples = self._samples_for_mode(mode)
        res = resolution or (1280, 720 if mode == RenderMode.PREVIEW else 1920, 1080)[-2:]
        if resolution is None:
            res = (1280, 720) if mode == RenderMode.PREVIEW else (1920, 1080)

        request = RenderRequest(
            scene=scene,
            mode=mode,
            resolution=res,
            samples=samples,
            output_path=output_path,
            camera_position=camera_position,
            camera_target=camera_target,
        )

        job = RenderJob(
            id=job_id,
            request=request,
            on_complete=on_complete,
        )
        self._jobs[job_id] = job
        self._queue.append(job_id)
        return job_id

    def run_sync(self, job_id: str) -> RenderJob:
        """Run a specific job synchronously (blocks until complete)."""
        job = self._jobs.get(job_id)
        if job is None:
            raise KeyError(f"Unknown job: {job_id}")
        self._execute(job)
        return job

    def run_next(self) -> Optional[RenderJob]:
        """Execute the next queued job if under concurrency limit."""
        if len(self._active) >= self._max_parallel:
            return None
        if not self._queue:
            return None
        job_id = self._queue.pop(0)
        job = self._jobs[job_id]
        self._active.append(job_id)
        self._execute(job)
        self._active.remove(job_id)
        return job

    def get_job(self, job_id: str) -> Optional[RenderJob]:
        return self._jobs.get(job_id)

    def pending_count(self) -> int:
        return len(self._queue)

    def active_count(self) -> int:
        return len(self._active)

    # ------------------------------------------------------------------
    # Internal execution
    # ------------------------------------------------------------------

    def _execute(self, job: RenderJob) -> None:
        job.status = JobStatus.RUNNING
        job.started_at = time.time()
        try:
            output = self._bridge.render(job.request)
            job.output_path = output
            job.status = JobStatus.COMPLETE
            job.progress = 1.0
            if job.on_complete:
                job.on_complete(job)
        except Exception as e:
            job.status = JobStatus.FAILED
            job.error = str(e)
        finally:
            job.finished_at = time.time()

    def _samples_for_mode(self, mode: RenderMode) -> int:
        return {
            RenderMode.PREVIEW: 32,
            RenderMode.PHOTOREAL: 512,
            RenderMode.TOPDOWN: 128,
            RenderMode.WALKTHROUGH: 64,
            RenderMode.MATERIAL_BOARD: 256,
        }.get(mode, 64)
