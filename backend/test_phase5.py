import unittest
from fastapi.testclient import TestClient
from app.main import app
from app.database import db
from seed_roadmap import seed_database

class TestMLSemanticSearch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.db = db
        if cls.db["months"].count_documents({}) == 0:
            seed_database()

    @classmethod
    def tearDownClass(cls):
        pass

    def test_search_endpoint_returns_ranked_results(self):
        res_python = self.client.get("/api/classroom/search?q=Python")
        self.assertEqual(res_python.status_code, 200)
        results_python = res_python.json()
        self.assertGreater(len(results_python), 0)
        self.assertTrue(
            any("python" in t["content"].lower() for t in results_python[:3])
        )

        res_agent = self.client.get("/api/classroom/search?q=agent%20orchestration")
        self.assertEqual(res_agent.status_code, 200)
        results_agent = res_agent.json()
        self.assertGreater(len(results_agent), 0)

if __name__ == "__main__":
    unittest.main()
