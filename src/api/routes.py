"""API route definitions."""

import logging
import uuid
from pathlib import Path
from enum import Enum

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from src.pipeline import run_pipeline

logger = logging.getLogger("autoforge.api")
router = APIRouter()

# In-memory project store (swap for Redis/DB in production)
_projects: dict[str, dict] = {}


class ProjectStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class CreateProjectRequest(BaseModel):
    idea: str = Field(..., min_length=5, max_length=2000, description="Story idea")


class CreateProjectResponse(BaseModel):
    project_id: str
    status: str


class ProjectDetailResponse(BaseModel):
    project_id: str
    status: str
    plan: dict | None = None
    shots: list[dict] | None = None
    video_path: str | None = None
    error: str | None = None


async def _run_background(project_id: str, idea: str) -> None:
    _projects[project_id]["status"] = ProjectStatus.RUNNING
    try:
        result = await run_pipeline(idea, project_id)
        _projects[project_id].update(
            status=ProjectStatus.COMPLETED,
            plan=result["plan"],
            shots=result["shots"],
            video_path=result["video_path"],
        )
    except Exception as e:
        logger.exception("[%s] Pipeline failed", project_id)
        _projects[project_id].update(status=ProjectStatus.FAILED, error=str(e))


@router.post("/projects", response_model=CreateProjectResponse, status_code=202)
async def create_project(request: CreateProjectRequest, background_tasks: BackgroundTasks):
    project_id = uuid.uuid4().hex[:12]
    _projects[project_id] = {"project_id": project_id, "status": ProjectStatus.PENDING}
    background_tasks.add_task(_run_background, project_id, request.idea)
    logger.info("[%s] Project queued", project_id)
    return CreateProjectResponse(project_id=project_id, status=ProjectStatus.PENDING)


@router.get("/projects/{project_id}", response_model=ProjectDetailResponse)
async def get_project(project_id: str):
    if project_id not in _projects:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectDetailResponse(**_projects[project_id])


@router.get("/projects/{project_id}/video")
async def get_video(project_id: str):
    if project_id not in _projects:
        raise HTTPException(status_code=404, detail="Project not found")
    video_path = _projects[project_id].get("video_path")
    if not video_path or not Path(video_path).exists():
        raise HTTPException(status_code=404, detail="Video not ready yet")
    return FileResponse(video_path, media_type="video/mp4", filename="autoforge_output.mp4")


@router.get("/projects/{project_id}/assets/{filename}")
async def get_asset(project_id: str, filename: str):
    from src.config import settings
    asset_path = Path(settings.output_dir) / project_id / filename
    if not asset_path.exists():
        raise HTTPException(status_code=404, detail="Asset not found")
    media_types = {
        ".mp3": "audio/mpeg",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
    }
    media_type = media_types.get(asset_path.suffix.lower(), "application/octet-stream")
    return FileResponse(asset_path, media_type=media_type)
