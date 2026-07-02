import os
from typing import List
from google import genai

FALLBACK_CAPSTONE_BLUEPRINT = """# Capstone Project Blueprint: Multi-Agent AI Engineer Sandbox

Given your progress in building the AI Engineer Classroom, your capstone is to assemble a unified sandbox system.

## 1. Project Title & Description
**Autonomous Courseware Coordinator (ACC)**
An intelligent workspace orchestration platform that monitors learning progression, auto-generates technical labs based on student weak spots, and streams time-synced audio reviews.

## 2. System Architecture
```mermaid
graph TD
    UI[Next.js Glassmorphic Portal] -->|GraphQL/JSON| API[FastAPI Orchestrator Router]
    API -->|Session logs| DB[(SQLite Database / SQLAlchemy)]
    API -->|Prompt Context| LLM[Gemini 2.5 Multi-Agent Engine]
    LLM --> ACC[Curriculum Adaptation Service]
    ACC -->|WebVTT track| UI
```

## 3. Database Schema Models
```python
class CapstoneLab(Base):
    __tablename__ = "capstone_labs"
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    difficulty_level = Column(String)
    code_boilerplate = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
```

## 4. Execution Milestones
- **Milestone 1:** Dynamic syllabus expansion based on performance telemetry.
- **Milestone 2:** Multi-Agent feedback loop simulating interactive teaching code reviewers.
- **Milestone 3:** Live WebVTT streaming audio explanation sync engine.

---
*Note: This personalized blueprint has been compiled based on your completed classroom topics.*
"""

def generate_capstone_blueprint(completed_topics: List[str]) -> str:
    """Uses Gemini 2.5 Flash to compile a tailored Capstone Project Spec, falling back upon key errors."""
    if not completed_topics:
        return (
            "# Personalized Capstone Blueprint\n\n"
            "**No topics completed yet!** Please mark some roadmap objectives from Months 1-5 "
            "as completed, then return here to compile your custom AI engineering portfolio project spec."
        )

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return FALLBACK_CAPSTONE_BLUEPRINT

    # Construct tailor-made LLM prompt
    prompt = (
        "You are a Senior AI Architect. The user of an interactive learning portal has completed "
        f"the following AI engineering curriculum topics: {', '.join(completed_topics)}.\n\n"
        "Generate a highly tailored, portfolio-grade Capstone Project Specification Blueprint in Markdown format.\n"
        "The project should creatively combine/apply the skills they have learned. Structure matches exactly:\n"
        "1. Project Title & Technical Overview\n"
        "2. Detailed System Architecture Block Diagrams Description\n"
        "3. Database Schema Models (SQLAlchemy Python code blocks representation)\n"
        "4. Core Agent Flow & Step-by-Step Execution Milestones\n"
        "Keep the design premium, cohesive, and deeply contextual to their history."
    )

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return response.text
    except Exception:
        return FALLBACK_CAPSTONE_BLUEPRINT
