import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from ..database import get_db
from ..models import Topic
from ..services.llm_generation import generate_material_for_topic, LessonMaterial
from ..services.vector_search import semantic_search_topics
from ..services.ml_reranker import hybrid_rerank
from ..services.capstone_orchestrator import generate_capstone_blueprint

router = APIRouter()

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

@router.get("/months", response_model=List[MonthSchema])
def get_months(db = Depends(get_db)):
    months = list(db["months"].find().sort("number", 1))
    result = []
    for m in months:
        weeks_list = []
        weeks = list(db["weeks"].find({"month_id": m["id"]}).sort("number", 1))
        for w in weeks:
            topics_list = []
            topics = list(db["topics"].find({"week_id": w["id"]}).sort("order_num", 1))
            for t in topics:
                progress = db["user_progress"].find_one({"topic_id": t["id"]})
                completed = progress["completed"] if progress else False
                topics_list.append(TopicSchema(
                    id=t["id"],
                    week_id=t["week_id"],
                    content=t["content"],
                    category=t["category"],
                    order_num=t["order_num"],
                    completed=completed
                ))
            weeks_list.append(WeekSchema(
                id=w["id"],
                month_id=w["month_id"],
                number=w["number"],
                title=w["title"],
                topics=topics_list
            ))
        result.append(MonthSchema(
            id=m["id"],
            number=m["number"],
            title=m["title"],
            focus=m.get("focus"),
            build_target=m.get("build_target"),
            weeks=weeks_list
        ))
    return result

@router.get("/weeks", response_model=List[WeekSchema])
def get_weeks(db = Depends(get_db)):
    weeks = list(db["weeks"].find().sort("number", 1))
    result = []
    for w in weeks:
        topics_list = []
        topics = list(db["topics"].find({"week_id": w["id"]}).sort("order_num", 1))
        for t in topics:
            progress = db["user_progress"].find_one({"topic_id": t["id"]})
            completed = progress["completed"] if progress else False
            topics_list.append(TopicSchema(
                id=t["id"],
                week_id=t["week_id"],
                content=t["content"],
                category=t["category"],
                order_num=t["order_num"],
                completed=completed
            ))
        result.append(WeekSchema(
            id=w["id"],
            month_id=w["month_id"],
            number=w["number"],
            title=w["title"],
            topics=topics_list
        ))
    return result

@router.get("/topics", response_model=List[TopicSchema])
def get_topics(db = Depends(get_db)):
    topics = list(db["topics"].find().sort([("week_id", 1), ("order_num", 1)]))
    result = []
    for t in topics:
        progress = db["user_progress"].find_one({"topic_id": t["id"]})
        completed = progress["completed"] if progress else False
        result.append(TopicSchema(
            id=t["id"],
            week_id=t["week_id"],
            content=t["content"],
            category=t["category"],
            order_num=t["order_num"],
            completed=completed
        ))
    return result

@router.post("/topics/{topic_id}/toggle", response_model=ToggleResponse)
def toggle_topic(topic_id: int, db = Depends(get_db)):
    topic = db["topics"].find_one({"id": topic_id})
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    progress = db["user_progress"].find_one({"topic_id": topic_id})
    if not progress:
        progress = {
            "topic_id": topic_id,
            "completed": True,
            "completed_at": datetime.datetime.utcnow()
        }
        db["user_progress"].insert_one(progress)
    else:
        new_completed = not progress["completed"]
        completed_at = datetime.datetime.utcnow() if new_completed else None
        db["user_progress"].update_one(
            {"topic_id": topic_id},
            {"$set": {"completed": new_completed, "completed_at": completed_at}}
        )
        progress = db["user_progress"].find_one({"topic_id": topic_id})
    return ToggleResponse(
        topic_id=progress["topic_id"],
        completed=progress["completed"],
        completed_at=progress.get("completed_at")
    )

@router.get("/classroom/status", response_model=ProgressStatusResponse)
def get_classroom_status(db = Depends(get_db)):
    total_topics = db["topics"].count_documents({})
    completed_topics = db["user_progress"].count_documents({"completed": True})
    progress_percent = (completed_topics / total_topics * 100) if total_topics > 0 else 0.0
    settings = db["user_settings"].find_one()
    current_topic_id = settings.get("current_topic_id") if settings else None
    return ProgressStatusResponse(
        total_topics=total_topics,
        completed_topics=completed_topics,
        progress_percent=round(progress_percent, 2),
        current_topic_id=current_topic_id
    )

@router.post("/classroom/current-lesson")
def update_current_lesson(update: LessonUpdateUpdate, db = Depends(get_db)):
    if update.topic_id is not None:
        topic = db["topics"].find_one({"id": update.topic_id})
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")
    settings = db["user_settings"].find_one()
    if not settings:
        db["user_settings"].insert_one({
            "current_topic_id": update.topic_id,
            "last_active_at": datetime.datetime.utcnow()
        })
    else:
        db["user_settings"].update_one(
            {},
            {"$set": {
                "current_topic_id": update.topic_id,
                "last_active_at": datetime.datetime.utcnow()
            }}
        )
    return {"current_topic_id": update.topic_id}

@router.get("/topics/{topic_id}/material", response_model=LessonMaterial)
def get_topic_material(topic_id: int, db = Depends(get_db)):
    topic = db["topics"].find_one({"id": topic_id})
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    cached = db["curriculum_cache"].find_one({"topic_id": topic_id})
    if cached:
        return LessonMaterial(
            technical_notes=cached["technical_notes"],
            quiz=cached["quiz"]
        )
    try:
        material = generate_material_for_topic(topic["content"])
        db["curriculum_cache"].insert_one({
            "topic_id": topic_id,
            "technical_notes": material.technical_notes,
            "quiz": [q.model_dump() for q in material.quiz]
        })
        return material
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM material generation failed: {str(e)}")

@router.get("/topics/{topic_id}/subtitles")
def get_topic_subtitles(topic_id: int, db = Depends(get_db)):
    topic = db["topics"].find_one({"id": topic_id})
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    vtt_content = "WEBVTT\n\n1\n00:00:00.000 --> 00:00:10.000\nVideo lecture content disabled. Please refer to Technical Notes below."
    return Response(content=vtt_content, media_type="text/vtt")

@router.get("/classroom/search")
def search_classroom_topics(q: str, db = Depends(get_db)):
    if not q.strip():
        return []
    try:
        all_topics = [Topic(t["id"], t["week_id"], t["content"], t["category"], t["order_num"]) for t in db["topics"].find()]
        candidates = semantic_search_topics(q, all_topics, top_k=15)
        ranked_results = hybrid_rerank(q, candidates, top_k=8)
        return [
            {
                "id": t.id,
                "week_id": t.week_id,
                "content": t.content,
                "category": t.category,
                "order_num": t.order_num,
                "completed": db["user_progress"].find_one({
                    "topic_id": t.id,
                    "completed": True
                }) is not None
            }
            for t in ranked_results
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search pipeline failed: {str(e)}")

@router.post("/classroom/capstone")
def create_personalized_capstone(db = Depends(get_db)):
    try:
        completed_progress = list(db["user_progress"].find({"completed": True}))
        completed_topic_ids = [p["topic_id"] for p in completed_progress]
        completed_topics = list(db["topics"].find({"id": {"$in": completed_topic_ids}}))
        topic_titles = [t["content"] for t in completed_topics]
        blueprint_content = generate_capstone_blueprint(topic_titles)
        return {"blueprint": blueprint_content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Capstone generation failed: {str(e)}")
