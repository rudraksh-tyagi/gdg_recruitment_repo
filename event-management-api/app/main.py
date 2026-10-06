from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.events import router as events_router
from app.core.config import settings
from app.db.session import close_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

    await close_database()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Asynchronous Event Management API built with "
        "FastAPI, SQLAlchemy 2.0 and Supabase PostgreSQL."
    ),
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(
    events_router,
    prefix="/api/v1",
)


@app.get(
    "/",
    tags=["Health"],
)
async def root():
    return {
        "message": "Event Management API is running",
        "version": settings.app_version,
    }


@app.get(
    "/health",
    tags=["Health"],
)
async def health_check():
    return {
        "status": "healthy",
    }