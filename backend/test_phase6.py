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
        verify_environment_keys()
        self.assertTrue(os.path.exists(LOG_FILE))

    def test_capstone_generation_empty(self):
        blueprint_empty = generate_capstone_blueprint([])
        self.assertIn("No topics completed yet", blueprint_empty)

    def test_capstone_generation_with_topics(self):
        test_topics = ["Intro to python syntax", "LangGraph design patterns", "Vector embeddings indexing"]
        blueprint_active = generate_capstone_blueprint(test_topics)
        self.assertTrue(blueprint_active.startswith("#"))
        self.assertIn("Milestone", blueprint_active)

    def test_capstone_endpoint(self):
        res_capstone = self.client.post("/api/classroom/capstone")
        self.assertEqual(res_capstone.status_code, 200)
        data = res_capstone.json()
        self.assertIn("blueprint", data)

if __name__ == "__main__":
    unittest.main()
