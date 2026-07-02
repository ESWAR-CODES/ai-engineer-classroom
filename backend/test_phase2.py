import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal, Base, engine
from app.models import Month, Week, Topic
from app.services import llm_generation

class TestClassroomAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create test DB tables
        Base.metadata.create_all(bind=engine)
        cls.client = TestClient(app)
        cls.db = SessionLocal()

        # Seed minimal test data if not already present
        if not cls.db.query(Month).first():
            m = Month(number=1, title="Test Month", focus="Testing", build_target="A Test API")
            cls.db.add(m)
            cls.db.flush()
            w = Week(month_id=m.id, number=1, title="Test Week")
            cls.db.add(w)
            cls.db.flush()
            t = Topic(week_id=w.id, content="Variables and structures", category="learn", order_num=1)
            cls.db.add(t)
            cls.db.commit()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

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
        # Get first topic
        topic = self.db.query(Topic).first()
        self.assertIsNotNone(topic)

        # Toggle to True
        response = self.client.post(f"/api/topics/{topic.id}/toggle")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["completed"])

        # Toggle to False
        response = self.client.post(f"/api/topics/{topic.id}/toggle")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["completed"])

    def test_classroom_status(self):
        response = self.client.get("/api/classroom/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("progress_percent", data)
        self.assertIn("completed_topics", data)

    def test_update_current_lesson(self):
        topic = self.db.query(Topic).first()
        response = self.client.post("/api/classroom/current-lesson", json={"topic_id": topic.id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["current_topic_id"], topic.id)

    @patch("google.genai.Client")
    def test_gemini_generation_mock(self, mock_client_class):
        # Setup mock client
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        # Setup mock response
        mock_response = MagicMock()
        mock_response.text = """{
            "voice_script": "Welcome students to variables learning.",
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

        # Execute call
        result = llm_generation.generate_material_for_topic("Variables")

        # Assert correct schema payload validation
        self.assertEqual(result.voice_script, "Welcome students to variables learning.")
        self.assertEqual(len(result.quiz), 1)
        self.assertEqual(result.quiz[0].correct_answer_idx, 1)

if __name__ == "__main__":
    unittest.main()
