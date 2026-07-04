import os
import re
from app.database import db

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
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    roadmap_path = os.path.join(base_dir, "AI Engineer Roadmap_ Zero to Hired in 6 Months.txt")
    if not os.path.exists(roadmap_path):
        print(f"Roadmap file not found at: {roadmap_path}")
        return
    db["topics"].delete_many({})
    db["weeks"].delete_many({})
    db["months"].delete_many({})
    with open(roadmap_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    current_month_id = None
    current_week_id = None
    topic_order = 0
    topic_id_counter = 1
    for line in lines:
        line_str = line.strip()
        if not line_str:
            continue
        month_match = re.match(r"^Month\s+(\d+)\s*[-:]\s*(.+)$", line_str, re.IGNORECASE)
        if month_match:
            month_num = int(month_match.group(1))
            month_title = month_match.group(2).strip()
            meta = MONTH_METADATA.get(month_num, {"focus": "", "build_target": ""})
            db["months"].insert_one({
                "id": month_num,
                "number": month_num,
                "title": month_title,
                "focus": meta["focus"],
                "build_target": meta["build_target"]
            })
            current_month_id = month_num
            current_week_id = None
            print(f"Added Month {month_num}: {month_title}")
            continue
        week_match = re.match(r"^Week\s+(\d+)\s*[-:]\s*(.+)$", line_str, re.IGNORECASE)
        if week_match:
            week_num = int(week_match.group(1))
            week_title = week_match.group(2).strip()
            if not current_month_id:
                print(f"Warning: Week found before Month initialization: {line_str}")
                continue
            db["weeks"].insert_one({
                "id": week_num,
                "month_id": current_month_id,
                "number": week_num,
                "title": week_title
            })
            current_week_id = week_num
            topic_order = 0
            print(f"  Added Week {week_num}: {week_title}")
            continue
        if line_str.startswith("?"):
            if not current_week_id:
                continue
            content = line_str[1:].strip()
            category = "learn"
            build_match = re.match(r"^Build\s*:\s*(.+)$", content, re.IGNORECASE)
            if build_match:
                category = "build"
                content = build_match.group(1).strip()
            topic_order += 1
            db["topics"].insert_one({
                "id": topic_id_counter,
                "week_id": current_week_id,
                "content": content,
                "category": category,
                "order_num": topic_order
            })
            print(f"    Added Topic: [{category.upper()}] {content[:40]}...")
            topic_id_counter += 1
    print("Database successfully seeded!")

if __name__ == "__main__":
    seed_database()
