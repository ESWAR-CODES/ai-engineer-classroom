import sys
from app.database import db
from seed_roadmap import seed_database

def verify():
    try:
        if db["months"].count_documents({}) == 0:
            seed_database()
        months = list(db["months"].find())
        weeks = list(db["weeks"].find())
        topics = list(db["topics"].find())
        print("--- VERIFICATION REPORT ---")
        print(f"Total Months: {len(months)}")
        print(f"Total Weeks:  {len(weeks)}")
        print(f"Total Topics: {len(topics)}")
        print("\nBreakdown by Category:")
        learn_count = sum(1 for t in topics if t["category"] == "learn")
        build_count = sum(1 for t in topics if t["category"] == "build")
        print(f" - Learn: {learn_count}")
        print(f" - Build: {build_count}")
        if len(months) != 6:
            print("Error: Expected 6 months, got", len(months))
            return False
        if len(weeks) != 24:
            print("Error: Expected 24 weeks, got", len(weeks))
            return False
        print("\nMonthly Overview:")
        for m in sorted(months, key=lambda x: x["number"]):
            print(f"Month {m['number']}: {m['title']}")
            print(f"  Focus: {m.get('focus')}")
            print(f"  Build: {m.get('build_target')}")
            print(f"  Weeks:")
            m_weeks = [w for w in weeks if w["month_id"] == m["id"]]
            for w in sorted(m_weeks, key=lambda x: x["number"]):
                w_topics = [t for t in topics if t["week_id"] == w["id"]]
                print(f"    - Week {w['number']}: {w['title']} ({len(w_topics)} items)")
        print("\nVerification successful! Database matches the initial curriculum specifications.")
        return True
    except Exception as e:
        print(f"Verification failed with: {e}")
        return False

if __name__ == "__main__":
    success = verify()
    sys.exit(0 if success else 1)
