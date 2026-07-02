import unittest
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import Topic

class TestMLSemanticSearch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.db = SessionLocal()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_search_endpoint_returns_ranked_results(self):
        print("\n=== RUNNING ML SEMANTIC SEARCH EVALUATION ===")
        
        # Test Query 1: Exact keyword match signals
        print("[TEST 1] Searching for 'Python'...")
        res_python = self.client.get("/api/classroom/search?q=Python")
        self.assertEqual(res_python.status_code, 200)
        results_python = res_python.json()
        
        # Display top 3 matching topics
        print("Top 3 returned topics for 'Python':")
        for i, t in enumerate(results_python[:3]):
            print(f"  {i+1}. [ID: {t['id']}] {t['content']}")

        # Assertions
        self.assertGreater(len(results_python), 0, "Should return matching results for 'Python'")
        self.assertTrue(
            any("python" in t["content"].lower() for t in results_python[:3]),
            "Top matched topics should contain key keyword 'Python'"
        )

        # Test Query 2: Semantic fuzzy concepts
        print("\n[TEST 2] Searching for 'agent orchestration'...")
        res_agent = self.client.get("/api/classroom/search?q=agent%20orchestration")
        self.assertEqual(res_agent.status_code, 200)
        results_agent = res_agent.json()
        
        print("Top 3 returned topics for 'agent orchestration':")
        for i, t in enumerate(results_agent[:3]):
            print(f"  {i+1}. [ID: {t['id']}] {t['content']}")
            
        self.assertGreater(len(results_agent), 0, "Should return results for semantic query")
        
        print("=== ML SEMANTIC SEARCH VALIDATION PASSED ===")

if __name__ == "__main__":
    unittest.main()
