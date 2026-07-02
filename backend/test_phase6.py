import os
import unittest
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import verify_environment_keys, LOG_FILE
from app.services.capstone_orchestrator import generate_capstone_blueprint

class TestProductionCapstone(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_production_logging_and_env(self):
        print("\n=== RUNNING SECURITY & ENV EVALUATION ===")
        verify_environment_keys()
        
        # Check logs initialization
        self.assertTrue(os.path.exists(LOG_FILE), "Log file should be created in the backend root.")
        print(f" -> Production logger verified. Rotates logs inside: {LOG_FILE}")

    def test_capstone_generation_empty(self):
        print("\n[TEST 2] Testing empty progress log telemetry...")
        blueprint_empty = generate_capstone_blueprint([])
        self.assertIn("No topics completed yet", blueprint_empty)
        print(" -> Correctly handles empty telemetry logs.")

    def test_capstone_generation_with_topics(self):
        print("\n[TEST 3] Testing active progress templates...")
        test_topics = ["Intro to python syntax", "LangGraph design patterns", "Vector embeddings indexing"]
        blueprint_active = generate_capstone_blueprint(test_topics)
        
        # Should contain structural markdown tags
        self.assertTrue(blueprint_active.startswith("#"), "Blueprint must start with markdown header.")
        self.assertIn("Milestone", blueprint_active, "Blueprint must contain execute milestones.")
        print(" -> Custom portfolio blueprint spec successfully compiled.")

    def test_capstone_endpoint(self):
        print("\n[TEST 4] Fetching client endpoint POST /api/classroom/capstone...")
        res_capstone = self.client.post("/api/classroom/capstone")
        self.assertEqual(res_capstone.status_code, 200)
        
        data = res_capstone.json()
        self.assertIn("blueprint", data)
        print(" -> API endpoint returned valid capability json.")
        
        print("=== PRODUCTION READY CAPSTONE EVALUATION PASSED ===")

if __name__ == "__main__":
    unittest.main()
