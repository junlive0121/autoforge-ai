"""API route definitions."""

import asyncio
import logging
from enum import Enum

from fastapi import APIRouter, BackgroundTasks, HTTPException
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
    import uuid

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
