from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import documents, pipeline, content, sessions, turns, media


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="Eksaminator API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router)
app.include_router(pipeline.router)
app.include_router(content.router)
app.include_router(sessions.router)
app.include_router(turns.router)
app.include_router(media.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
