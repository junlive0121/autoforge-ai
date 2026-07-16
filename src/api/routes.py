"""API route definitions."""

from fastapi import APIRouter

router = APIRouter()


@router.post("/projects")
async def create_project():
    raise NotImplementedError
