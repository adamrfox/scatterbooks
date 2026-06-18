from contextlib import asynccontextmanager
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import FileResponse

from app.bootstrap import bootstrap_admin
from app.database import SessionLocal
from app.routers import auth, books, categories, editions, images, users

BACKEND_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BACKEND_DIR / "app" / "static"


def run_migrations() -> None:
    alembic_cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    command.upgrade(alembic_cfg, "head")


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_migrations()
    db = SessionLocal()
    try:
        bootstrap_admin(db)
    finally:
        db.close()
    yield


app = FastAPI(title="scatterbooks", lifespan=lifespan)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(books.router)
app.include_router(categories.router)
app.include_router(editions.router)
app.include_router(images.router)


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_frontend(full_path: str) -> FileResponse:
    """Serve the built React app, falling back to index.html for any
    unrecognized path so client-side routing (React Router) can take over --
    e.g. a hard refresh on /books/42 should still load the SPA shell.
    Registered last so it never shadows the /api/* routers above.
    """
    candidate = STATIC_DIR / full_path
    if full_path and candidate.is_file():
        return FileResponse(candidate)

    index_path = STATIC_DIR / "index.html"
    if not index_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return FileResponse(index_path)
