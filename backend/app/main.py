import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import classroom
from .database import engine, Base

app = FastAPI(title="AI Engineer Classroom API")

Base.metadata.create_all(bind=engine)

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
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(classroom.router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Welcome to the AI Engineer Classroom API!"}