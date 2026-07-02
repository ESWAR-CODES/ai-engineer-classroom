import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import classroom
from .database import engine, Base, SessionLocal
from .models import Month

app = FastAPI(title="AI Engineer Classroom API")

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

env_origins = os.getenv("ALLOWED_ORIGINS")
if env_origins:
    origins.extend([origin.strip() for origin in env_origins.split(",")])
else:
    origins.append("*")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False if "*" in origins else True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

@app.on_event("startup")
def startup_event():
    try:
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if backend_dir not in sys.path:
            sys.path.append(backend_dir)
        from seed_roadmap import seed_database
        db = SessionLocal()
        try:
            if not db.query(Month).first():
                seed_database()
        finally:
            db.close()
    except Exception:
        import traceback
        traceback.print_exc()

app.include_router(classroom.router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Welcome to the AI Engineer Classroom API!"}