import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import classroom

app = FastAPI(title="AI Engineer Classroom API")

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://ai-class-taupe.vercel.app",
    "https://ai-engineer-classroom.vercel.app",
]

env_origins = os.getenv("ALLOWED_ORIGINS")
if env_origins:
    origins.extend([origin.strip() for origin in env_origins.split(",")])

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    try:
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if backend_dir not in sys.path:
            sys.path.append(backend_dir)
        from seed_roadmap import seed_database
        from app.database import db
        if db["months"].count_documents({}) == 0:
            seed_database()
    except Exception:
        import traceback
        traceback.print_exc()

app.include_router(classroom.router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Welcome to the AI Engineer Classroom API!"}