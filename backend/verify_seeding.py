from app.database import SessionLocal
from app.models import Month, Week, Topic

def verify():
    db = SessionLocal()
    try:
        months = db.query(Month).all()
        weeks = db.query(Week).all()
        topics = db.query(Topic).all()

        print("--- VERIFICATION REPORT ---")
        print(f"Total Months: {len(months)}")
        print(f"Total Weeks:  {len(weeks)}")
        print(f"Total Topics: {len(topics)}")

        print("\nBreakdown by Category:")
        learn_count = sum(1 for t in topics if t.category == "learn")
        build_count = sum(1 for t in topics if t.category == "build")
        print(f" - Learn: {learn_count}")
        print(f" - Build: {build_count}")

        # Check expectations
        if len(months) != 6:
            print("Error: Expected 6 months, got", len(months))
            return False
        if len(weeks) != 24:
            print("Error: Expected 24 weeks, got", len(weeks))
            return False
            
        print("\nMonthly Overview:")
        for m in months:
            print(f"Month {m.number}: {m.title}")
            print(f"  Focus: {m.focus}")
            print(f"  Build: {m.build_target}")
            print(f"  Weeks:")
            for w in m.weeks:
                print(f"    - Week {w.number}: {w.title} ({len(w.topics)} items)")
        
        print("\nVerification successful! Database matches the initial curriculum specifications.")
        return True
    except Exception as e:
        print(f"Verification failed with: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = verify()
    import sys
    sys.exit(0 if success else 1)
