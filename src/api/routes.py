"""API route definitions."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class CreateProjectRequest(BaseModel):
    idea: str


class CreateProjectResponse(BaseModel):
    project_id: str
    status: str
    message: str


@router.post("/projects", response_model=CreateProjectResponse)
async def create_project(request: CreateProjectRequest) -> CreateProjectResponse:
    """Kick off a new video production pipeline from a story idea."""
    raise HTTPException(
        status_code=501,
        detail="Pipeline not yet implemented. Agent stubs are in place.",
    )
