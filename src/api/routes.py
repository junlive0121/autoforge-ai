"""API route definitions."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.pipeline import run_pipeline

router = APIRouter()


class CreateProjectRequest(BaseModel):
    idea: str


class CreateProjectResponse(BaseModel):
    project_id: str
    status: str
    video_path: str
    plan: dict
    shots: list[dict]


@router.post("/projects", response_model=CreateProjectResponse)
async def create_project(request: CreateProjectRequest) -> CreateProjectResponse:
    """Kick off a new video production pipeline from a story idea."""
    try:
        result = await run_pipeline(request.idea)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return CreateProjectResponse(**result)
