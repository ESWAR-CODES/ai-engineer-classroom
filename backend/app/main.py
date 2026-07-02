from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import classroom
from .database import engine, Base

app = FastAPI(title="AI Engineer Classroom API")

# Create database tables automatically (fallback)
Base.metadata.create_all(bind=engine)

# Configure CORS for Next.js app (running on localhost:3000)
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

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
