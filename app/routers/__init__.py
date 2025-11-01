from fastapi import APIRouter
from .capabilities import router as capabilities

api = APIRouter()
api.include_router(capabilities)

