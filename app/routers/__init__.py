from fastapi import APIRouter
from .capabilities import router as capabilities
from .protocols import router as protocols
from .ewl import router as ewl

api = APIRouter()
api.include_router(capabilities)
api.include_router(protocols)
api.include_router(ewl)
