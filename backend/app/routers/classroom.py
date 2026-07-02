import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Month, Week, Topic, UserProgress, UserSettings
from ..services.llm_generation import generate_material_for_topic, LessonMaterial
from ..services.media_orchestrator import generate_vtt_subtitles
from ..services.vector_search import semantic_search_topics
from ..services.ml_reranker import hybrid_rerank
from ..services.capstone_orchestrator import generate_capstone_blueprint

router = APIRouter()

# --- Pydantic Schemas for Requests and Responses ---

class TopicSchema(BaseModel):
    id: int
    week_id: int
    content: str
    category: str
    order_num: int
    completed: bool = False

    class Config:
        from_attributes = True

class WeekSchema(BaseModel):
    id: int
    month_id: int
    number: int
    title: str
    topics: List[TopicSchema] = []

    class Config:
        from_attributes = True

class MonthSchema(BaseModel):
    id: int
    number: int
    title: str
    focus: Optional[str] = None
    build_target: Optional[str] = None
    weeks: List[WeekSchema] = []

    class Config:
        from_attributes = True

class ToggleResponse(BaseModel):
    topic_id: int
    completed: bool
    completed_at: Optional[datetime.datetime] = None

class ProgressStatusResponse(BaseModel):
    total_topics: int
    completed_topics: int
    progress_percent: float
    current_topic_id: Optional[int] = None

class LessonUpdateUpdate(BaseModel):
    topic_id: Optional[int] = None

# --- API Endpoints ---

@router.get("/months", response_model=List[MonthSchema])
def get_months(db: Session = Depends(get_db)):
    """Fetch all months along with nested weeks and topics (with completion status)."""
    months = db.query(Month).order_by(Month.number).all()
    result = []
    for m in months:
        weeks_list = []
        for w in m.weeks:
            topics_list = []
            for t in w.topics:
                completed = t.progress.completed if t.progress else False
                topics_list.append(TopicSchema(
                    id=t.id,
                    week_id=t.week_id,
                    content=t.content,
                    category=t.category,
                    order_num=t.order_num,
                    completed=completed
                ))
            weeks_list.append(WeekSchema(
                id=w.id,
                month_id=w.month_id,
                number=w.number,
                title=w.title,
                topics=topics_list
            ))
        result.append(MonthSchema(
            id=m.id,
            number=m.number,
            title=m.title,
            focus=m.focus,
            build_target=m.build_target,
            weeks=weeks_list
        ))
    return result

@router.get("/weeks", response_model=List[WeekSchema])
def get_weeks(db: Session = Depends(get_db)):
    """Fetch all weeks along with nested topics (with completion status)."""
    weeks = db.query(Week).order_by(Week.number).all()
    result = []
    for w in weeks:
        topics_list = []
        for t in w.topics:
            completed = t.progress.completed if t.progress else False
            topics_list.append(TopicSchema(
                id=t.id,
                week_id=t.week_id,
                content=t.content,
                category=t.category,
                order_num=t.order_num,
                completed=completed
            ))
        result.append(WeekSchema(
            id=w.id,
            month_id=w.month_id,
            number=w.number,
            title=w.title,
            topics=topics_list
        ))
    return result

@router.get("/topics", response_model=List[TopicSchema])
def get_topics(db: Session = Depends(get_db)):
    """Fetch all topics with their individual completion status."""
    topics = db.query(Topic).order_by(Topic.week_id, Topic.order_num).all()
    result = []
    for t in topics:
        completed = t.progress.completed if t.progress else False
        result.append(TopicSchema(
            id=t.id,
            week_id=t.week_id,
            content=t.content,
            category=t.category,
            order_num=t.order_num,
            completed=completed
        ))
    return result

@router.post("/topics/{topic_id}/toggle", response_model=ToggleResponse)
def toggle_topic(topic_id: int, db: Session = Depends(get_db)):
    """Toggle a topic's completion status. Creates a progress record if none exists."""
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    progress = db.query(UserProgress).filter(UserProgress.topic_id == topic_id).first()
    if not progress:
        progress = UserProgress(topic_id=topic_id, completed=True, completed_at=datetime.datetime.utcnow())
        db.add(progress)
    else:
        progress.completed = not progress.completed
        if progress.completed:
            progress.completed_at = datetime.datetime.utcnow()
        else:
            progress.completed_at = None
    db.commit()
    db.refresh(progress)

    return ToggleResponse(
        topic_id=progress.topic_id,
        completed=progress.completed,
        completed_at=progress.completed_at
    )

@router.get("/classroom/status", response_model=ProgressStatusResponse)
def get_classroom_status(db: Session = Depends(get_db)):
    """Returns general progress analytics (total, completed, completion percentage, active lesson)."""
    total_topics = db.query(Topic).count()
    completed_topics = db.query(UserProgress).filter(UserProgress.completed == True).count()
    progress_percent = (completed_topics / total_topics * 100) if total_topics > 0 else 0.0

    settings = db.query(UserSettings).first()
    current_topic_id = settings.current_topic_id if settings else None

    return ProgressStatusResponse(
        total_topics=total_topics,
        completed_topics=completed_topics,
        progress_percent=round(progress_percent, 2),
        current_topic_id=current_topic_id
    )

@router.post("/classroom/current-lesson")
def update_current_lesson(update: LessonUpdateUpdate, db: Session = Depends(get_db)):
    """Updates the user's active/current lesson tracking pointer."""
    if update.topic_id is not None:
        topic = db.query(Topic).filter(Topic.id == update.topic_id).first()
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")

    settings = db.query(UserSettings).first()
    if not settings:
        settings = UserSettings(current_topic_id=update.topic_id)
        db.add(settings)
    else:
        settings.current_topic_id = update.topic_id

    db.commit()
    return {"current_topic_id": settings.current_topic_id}

@router.get("/topics/{topic_id}/material", response_model=LessonMaterial)
def get_topic_material(topic_id: int, db: Session = Depends(get_db)):
    """Fetches topic by ID and runs Gemini content generation to produce structured lesson material."""
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
        
    try:
        material = generate_material_for_topic(topic.content)
        return material
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM material generation failed: {str(e)}")

@router.get("/topics/{topic_id}/subtitles")
def get_topic_subtitles(topic_id: int, db: Session = Depends(get_db)):
    """Generates WebVTT subtitles dynamically for the selected topic's voice script."""
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
        
    try:
        material = generate_material_for_topic(topic.content)
        vtt_content = generate_vtt_subtitles(material.voice_script)
        return Response(content=vtt_content, media_type="text/vtt")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate subtitles: {str(e)}")

@router.get("/classroom/search")
def search_classroom_topics(q: str, db: Session = Depends(get_db)):
    """Search for relevant curriculum topics using semantic embedding lookup + ML hybrid re-ranking."""
    if not q.strip():
        return []
        
    try:
        all_topics = db.query(Topic).all()
        candidates = semantic_search_topics(q, all_topics, top_k=15)
        ranked_results = hybrid_rerank(q, candidates, top_k=8)
        
        return [
            {
                "id": t.id,
                "week_id": t.week_id,
                "content": t.content,
                "category": t.category,
                "order_num": t.order_num,
                "completed": db.query(UserProgress).filter(
                    UserProgress.topic_id == t.id,
                    UserProgress.completed == True
                ).first() is not None
            }
            for t in ranked_results
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search pipeline failed: {str(e)}")

@router.post("/classroom/capstone")
def create_personalized_capstone(db: Session = Depends(get_db)):
    """Analyze user progress logs and generate a custom portfolio Capstone blueprint."""
    try:
        completed_topics = db.query(Topic).join(
            UserProgress, Topic.id == UserProgress.topic_id
        ).filter(
            UserProgress.completed == True
        ).all()
        
        topic_titles = [t.content for t in completed_topics]
        blueprint_content = generate_capstone_blueprint(topic_titles)
        return {"blueprint": blueprint_content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Capstone generation failed: {str(e)}")
