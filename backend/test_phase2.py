import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.database import db
from app.services import llm_generation

class TestClassroomAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.db = db
        if cls.db["months"].count_documents({}) == 0:
            cls.db["months"].insert_one({
                "id": 1,
                "number": 1,
                "title": "Test Month",
                "focus": "Testing",
                "build_target": "A Test API"
            })
            cls.db["weeks"].insert_one({
                "id": 1,
                "month_id": 1,
                "number": 1,
                "title": "Test Week"
            })
            cls.db["topics"].insert_one({
                "id": 1,
                "week_id": 1,
                "content": "Variables and structures",
                "category": "learn",
                "order_num": 1
            })

    @classmethod
    def tearDownClass(cls):
        pass

    def test_get_months(self):
        response = self.client.get("/api/months")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreater(len(data), 0)
        self.assertIn("weeks", data[0])
        self.assertIn("topics", data[0]["weeks"][0])

    def test_get_weeks(self):
        response = self.client.get("/api/weeks")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreater(len(data), 0)
        self.assertIn("topics", data[0])

    def test_get_topics(self):
        response = self.client.get("/api/topics")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreater(len(data), 0)
        self.assertIn("completed", data[0])

    def test_toggle_topic_completion(self):
        topic = self.db["topics"].find_one()
        self.assertIsNotNone(topic)
        topic_id = topic["id"]
        response = self.client.post(f"/api/topics/{topic_id}/toggle")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["completed"])
        response = self.client.post(f"/api/topics/{topic_id}/toggle")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["completed"])

    def test_classroom_status(self):
        response = self.client.get("/api/classroom/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("progress_percent", data)
        self.assertIn("completed_topics", data)

    def test_update_current_lesson(self):
        topic = self.db["topics"].find_one()
        topic_id = topic["id"]
        response = self.client.post("/api/classroom/current-lesson", json={"topic_id": topic_id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["current_topic_id"], topic_id)

    @patch("google.genai.Client")
    def test_gemini_generation_mock(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.text = """{
            "technical_notes": "# Variables\\n\\nNotes on variables.",
            "quiz": [
                {
                    "question": "What is Python?",
                    "options": ["A snake", "A language", "A tool"],
                    "correct_answer_idx": 1
                }
            ]
        }"""
        mock_client.models.generate_content.return_value = mock_response
        result = llm_generation.generate_material_for_topic("Variables")
        self.assertEqual(result.technical_notes, "# Variables\n\nNotes on variables.")
        self.assertEqual(len(result.quiz), 1)
        self.assertEqual(result.quiz[0].correct_answer_idx, 1)

if __name__ == "__main__":
    unittest.main()
