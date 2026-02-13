"""API routers for the application."""

# Import all routers here to make them easily importable
from backend.app.features.llm.llm_demo import router as llm_router

__all__ = [
    'llm_router',
]
