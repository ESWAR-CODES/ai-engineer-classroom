import os
import re
from sqlalchemy.orm import Session
from app.database import engine, Base, SessionLocal
from app.models import Month, Week, Topic

# Define Month Focus and Build targets as specified in the roadmap overview table
MONTH_METADATA = {
    1: {
        "focus": "Python, Git & Engineering Basics",
        "build_target": "A CLI app pushed to GitHub"
    },
    2: {
        "focus": "Data, Text & Embeddings Foundations",
        "build_target": "A semantic search prototype"
    },
    3: {
        "focus": "Generative AI & Prompt Engineering",
        "build_target": "An LLM-powered data extractor"
    },
    4: {
        "focus": "RAG, Vector Stores & Frameworks",
        "build_target": "A \"Chat with your docs\" app"
    },
    5: {
        "focus": "Machine Learning Foundations",
        "build_target": "A re-ranker that boosts your RAG"
    },
    6: {
        "focus": "Agentic Systems, Production & Capstone",
        "build_target": "A deployed AI product on GitHub"
    }
}

def seed_database():
    # Path to the roadmap text file
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    roadmap_path = os.path.join(base_dir, "AI Engineer Roadmap_ Zero to Hired in 6 Months.txt")

    if not os.path.exists(roadmap_path):
        print(f"Roadmap file not found at: {roadmap_path}")
        return

    print("Creating database tables if they do not exist...")
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()
    try:
        # Check if database is already seeded
        if db.query(Month).first():
            print("Database already has data. Clearing existing records to re-seed...")
            db.query(Topic).delete()
            db.query(Week).delete()
            db.query(Month).delete()
            db.commit()

        print(f"Parsing roadmap file: {roadmap_path}")
        with open(roadmap_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        current_month = None
        current_week = None
        topic_order = 0

        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue

            # Parse Month (e.g., "Month 1 - Python, Git & Engineering Basics" or "Month 1: ...")
            month_match = re.match(r"^Month\s+(\d+)\s*[-:]\s*(.+)$", line_str, re.IGNORECASE)
            if month_match:
                month_num = int(month_match.group(1))
                month_title = month_match.group(2).strip()
                
                # Fetch focus and build target from metadata
                meta = MONTH_METADATA.get(month_num, {"focus": "", "build_target": ""})
                
                current_month = Month(
                    number=month_num,
                    title=month_title,
                    focus=meta["focus"],
                    build_target=meta["build_target"]
                )
                db.add(current_month)
                db.flush()  # to get current_month.id
                current_week = None
                print(f"Added Month {month_num}: {month_title}")
                continue

            # Parse Week (e.g., "Week 1: Python Fundamentals" or "Week 1 - ...")
            week_match = re.match(r"^Week\s+(\d+)\s*[-:]\s*(.+)$", line_str, re.IGNORECASE)
            if week_match:
                week_num = int(week_match.group(1))
                week_title = week_match.group(2).strip()

                if not current_month:
                    print(f"Warning: Week found before Month initialization: {line_str}")
                    continue

                current_week = Week(
                    month_id=current_month.id,
                    number=week_num,
                    title=week_title
                )
                db.add(current_week)
                db.flush()  # to get current_week.id
                topic_order = 0
                print(f"  Added Week {week_num}: {week_title}")
                continue

            # Parse Topic item (e.g., "? Learn variables, data types...")
            if line_str.startswith("?"):
                if not current_week:
                    # Skip if no week is active (could be help text in the document)
                    continue

                content = line_str[1:].strip()
                
                # Determine if it's a build task or a learn task
                category = "learn"
                build_match = re.match(r"^Build\s*:\s*(.+)$", content, re.IGNORECASE)
                if build_match:
                    category = "build"
                    content = build_match.group(1).strip()

                topic_order += 1
                topic = Topic(
                    week_id=current_week.id,
                    content=content,
                    category=category,
                    order_num=topic_order
                )
                db.add(topic)
                print(f"    Added Topic: [{category.upper()}] {content[:40]}...")

        db.commit()
        print("Database successfully seeded!")
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
