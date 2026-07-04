import time
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.database import db
from app.services.llm_generation import LessonMaterial, QuizQuestion
from seed_roadmap import seed_database

class TestEndToEndPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.db = db
        if cls.db["months"].count_documents({}) == 0:
            seed_database()
        cls.mock_material = LessonMaterial(
            technical_notes="# AI Engineering Basics\n\nWelcome to neural nodes. Here is some **bold text** and `code` block.",
            quiz=[
                QuizQuestion(question="What is an AI agent?", options=["A program that acts dynamically", "A database", "A compiler"], correct_answer_idx=0),
                QuizQuestion(question="Which model handles unstructured input?", options=["LLM", "CSV", "Excel"], correct_answer_idx=0),
                QuizQuestion(question="What is WebVTT?", options=["Web Video Text Tracks", "A compiler config", "A database file"], correct_answer_idx=0),
            ]
        )
        cls.patcher = patch("app.routers.classroom.generate_material_for_topic", return_value=cls.mock_material)
        cls.patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls.patcher.stop()

    def test_e2e_lifecycle(self):
        topic = self.db["topics"].find_one()
        self.assertIsNotNone(topic)
        topic_id = topic["id"]
        res_settings = self.client.post("/api/classroom/current-lesson", json={"topic_id": topic_id})
        self.assertEqual(res_settings.status_code, 200)
        self.assertEqual(res_settings.json()["current_topic_id"], topic_id)
        start_time = time.time()
        res_material = self.client.get(f"/api/topics/{topic_id}/material")
        latency = time.time() - start_time
        self.assertEqual(res_material.status_code, 200)
        material_data = res_material.json()
        self.assertIn("technical_notes", material_data)
        self.assertIn("quiz", material_data)
        self.assertNotIn("voice_script", material_data)
        quiz = material_data["quiz"]
        self.assertEqual(len(quiz), 3)
        res_sub = self.client.get(f"/api/topics/{topic_id}/subtitles")
        self.assertEqual(res_sub.status_code, 200)
        self.assertIn("text/vtt", res_sub.headers["content-type"])
        vtt_text = res_sub.text
        self.assertTrue(vtt_text.startswith("WEBVTT"))
        res_status_prev = self.client.get("/api/classroom/status")
        initial_completed = res_status_prev.json()["completed_topics"]
        res_toggle1 = self.client.post(f"/api/topics/{topic_id}/toggle")
        self.assertEqual(res_toggle1.status_code, 200)
        self.assertTrue(res_toggle1.json()["completed"])
        res_status_post = self.client.get("/api/classroom/status")
        new_completed = res_status_post.json()["completed_topics"]
        self.assertEqual(new_completed, initial_completed + 1)
        res_toggle2 = self.client.post(f"/api/topics/{topic_id}/toggle")
        self.assertEqual(res_toggle2.status_code, 200)
        self.assertFalse(res_toggle2.json()["completed"])
        res_status_final = self.client.get("/api/classroom/status")
        self.assertEqual(res_status_final.json()["completed_topics"], initial_completed)

if __name__ == "__main__":
    unittest.main()
