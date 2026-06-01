"""File upload endpoints: floor plans, PDFs, inspiration images."""

from __future__ import annotations
import os
import shutil
import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

router = APIRouter(prefix="/upload", tags=["upload"])

UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", "/tmp/interior_ai/uploads"))
ALLOWED_EXTENSIONS = {
    ".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif",
    ".dxf", ".ifc", ".glb", ".fbx", ".webp",
}
MAX_FILE_SIZE_MB = 100


@router.post("/floor-plan")
async def upload_floor_plan(
    file: UploadFile = File(...),
    session_id: str = Form(default=""),
):
    """Upload a builder floor plan (PDF, image, DXF, or IFC)."""
    _validate_file(file.filename, file.size)
    file_path = await _save_upload(file, session_id, "floor_plans")
    file_type = _detect_type(file.filename)
    return {
        "status": "uploaded",
        "session_id": session_id or _new_session(),
        "file_path": str(file_path),
        "file_type": file_type,
        "filename": file.filename,
    }


@router.post("/inspiration")
async def upload_inspiration(
    file: UploadFile = File(...),
    session_id: str = Form(default=""),
):
    """Upload an inspiration image for palette and style extraction."""
    _validate_file(file.filename, file.size)
    file_path = await _save_upload(file, session_id, "inspiration")
    return {
        "status": "uploaded",
        "session_id": session_id or _new_session(),
        "file_path": str(file_path),
        "filename": file.filename,
    }


@router.post("/room-photo")
async def upload_room_photo(
    file: UploadFile = File(...),
    session_id: str = Form(default=""),
):
    """Upload a room photograph for depth estimation and scene reconstruction."""
    _validate_file(file.filename, file.size)
    file_path = await _save_upload(file, session_id, "room_photos")
    return {
        "status": "uploaded",
        "session_id": session_id or _new_session(),
        "file_path": str(file_path),
        "filename": file.filename,
    }


@router.post("/furniture-model")
async def upload_furniture_model(
    file: UploadFile = File(...),
    asset_id: str = Form(...),
    asset_name: str = Form(default=""),
    category: str = Form(default="decor"),
):
    """Upload a custom 3D furniture model (.glb or .fbx)."""
    _validate_file(file.filename, file.size)
    if Path(file.filename).suffix.lower() not in {".glb", ".fbx", ".obj"}:
        raise HTTPException(400, "Only .glb, .fbx, or .obj files accepted for furniture")
    file_path = await _save_upload(file, asset_id, "furniture")
    return {
        "status": "uploaded",
        "asset_id": asset_id,
        "file_path": str(file_path),
    }


# ── Helpers ──────────────────────────────────────────────────────────────────

def _validate_file(filename: str, size: int | None) -> None:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported file type: {ext}")
    if size and size > MAX_FILE_SIZE_MB * 1_048_576:
        raise HTTPException(413, f"File too large (max {MAX_FILE_SIZE_MB}MB)")


async def _save_upload(file: UploadFile, prefix: str, subdir: str) -> Path:
    dest_dir = UPLOAD_DIR / subdir / (prefix or "shared")
    dest_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(file.filename).suffix
    dest = dest_dir / f"{uuid.uuid4().hex[:12]}{suffix}"
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return dest


def _detect_type(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    return {
        ".pdf": "pdf",
        ".dxf": "dxf",
        ".ifc": "ifc",
        ".glb": "3d_model",
        ".fbx": "3d_model",
    }.get(ext, "image")


def _new_session() -> str:
    return uuid.uuid4().hex[:12]
