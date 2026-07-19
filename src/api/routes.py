"""API route definitions."""

import logging
import uuid
from enum import Enum

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from src.config import settings
from src.core.file_protocol import UnsafePathError
from src.core.media_integrity import safe_error_message
from src.demo_pipeline import run_demo_pipeline
from src.pipeline import run_pipeline
from src.repositories.project_repository import ProjectRepository
from src.ws import broadcast

logger = logging.getLogger("autoforge.api")
router = APIRouter()
project_repository = ProjectRepository(settings.output_dir)


class ProjectStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


class CreateProjectRequest(BaseModel):
    idea: str = Field(..., min_length=5, max_length=2000, description="Story idea")
    demo: bool = Field(
        default=False,
        description="Run the deterministic classroom sample without provider calls",
    )


class CreateProjectResponse(BaseModel):
    project_id: str
    status: str


class ProjectDetailResponse(BaseModel):
    project_id: str
    status: str
    plan: dict | None = None
    shots: list[dict] | None = None
    video_path: str | None = None
    video_metadata: dict | None = None
    error: str | None = None


async def _run_background(project_id: str, idea: str, demo: bool = False) -> None:
    try:
        project_repository.update(project_id, ProjectStatus.RUNNING)
        runner = run_demo_pipeline if demo else run_pipeline
        result = await runner(idea, project_id)
        project_repository.update(
            project_id,
            ProjectStatus.COMPLETED,
            plan=result["plan"],
            shots=result["shots"],
            video_path=result["video_path"],
            video_metadata=result["video_metadata"],
            error=None,
        )
    except Exception as e:
        logger.exception("[%s] Pipeline failed", project_id)
        public_error = safe_error_message(e)
        try:
            project_repository.update(
                project_id,
                ProjectStatus.FAILED,
                error=public_error,
            )
        except Exception:
            logger.exception("[%s] Failed to persist failure state", project_id)
        await broadcast(
            project_id,
            {"stage": "error", "message": public_error},
        )


@router.post("/projects", response_model=CreateProjectResponse, status_code=202)
async def create_project(request: CreateProjectRequest, background_tasks: BackgroundTasks):
    project_id = uuid.uuid4().hex[:12]
    project_repository.create(project_id, request.idea, demo=request.demo)
    background_tasks.add_task(
        _run_background,
        project_id,
        request.idea,
        request.demo,
    )
    logger.info("[%s] Project queued", project_id)
    return CreateProjectResponse(project_id=project_id, status=ProjectStatus.PENDING)


@router.get("/projects/{project_id}", response_model=ProjectDetailResponse)
async def get_project(project_id: str):
    try:
        project = project_repository.get(project_id)
    except (FileNotFoundError, ValueError, UnsafePathError):
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectDetailResponse(**project)


@router.get("/projects/{project_id}/video")
async def get_video(project_id: str):
    try:
        project = project_repository.get(project_id)
    except (FileNotFoundError, ValueError, UnsafePathError):
        raise HTTPException(status_code=404, detail="Project not found")
    if project.get("status") != ProjectStatus.COMPLETED:
        raise HTTPException(status_code=404, detail="Video not ready yet")
    try:
        video_path = project_repository.project_file(
            project_id,
            "final.mp4",
            require_exists=True,
        )
    except (FileNotFoundError, ValueError, UnsafePathError):
        raise HTTPException(status_code=404, detail="Video not ready yet")
    return FileResponse(video_path, media_type="video/mp4", filename="autoforge_output.mp4")


@router.get("/projects/{project_id}/assets/{filename}")
async def get_asset(project_id: str, filename: str):
    media_types = {
        ".mp3": "audio/mpeg",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
    }
    try:
        asset_path = project_repository.project_file(
            project_id,
            filename,
            require_exists=True,
        )
    except (FileNotFoundError, ValueError, UnsafePathError):
        raise HTTPException(status_code=404, detail="Asset not found")
    media_type = media_types.get(asset_path.suffix.lower())
    if media_type is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    return FileResponse(asset_path, media_type=media_type)
