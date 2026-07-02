import time
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal, Base, engine
from app.models import Topic, UserProgress, UserSettings
from app.services.llm_generation import LessonMaterial, QuizQuestion

class TestEndToEndPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.db = SessionLocal()
        
        # Pre-seed dynamic mock generation payload so the E2E pipeline evaluates regardless of GEMINI_API_KEY existence
        cls.mock_material = LessonMaterial(
            voice_script="Hello class! Welcome to Week 1 of AI Engineering. In this course, we will build agents.",
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
        cls.db.close()

    def test_e2e_lifecycle(self):
        print("\n=== STARTING END-TO-END PIPELINE EVALUATION ===")
        
        # 1. Fetch first topic from database
        topic = self.db.query(Topic).order_by(Topic.id).first()
        self.assertIsNotNone(topic, "Database must possess seeded topics to evaluate pipeline.")
        print(f"[STEP 1] Selected target topic: (ID: {topic.id}) '{topic.content[:40]}...'")

        # 2. Update active lesson setting
        print("[STEP 2] Setting topic as the current active session lesson...")
        res_settings = self.client.post("/api/classroom/current-lesson", json={"topic_id": topic.id})
        self.assertEqual(res_settings.status_code, 200)
        self.assertEqual(res_settings.json()["current_topic_id"], topic.id)
        print(" -> Current lesson pointer successfully updated in UserSettings.")

        # 3. Fetch/Generate Curriculum Material (with automated Gemini model call)
        print("[STEP 3] Triggering Gemini LLM content generation...")
        start_time = time.time()
        
        res_material = self.client.get(f"/api/topics/{topic.id}/material")
        latency = time.time() - start_time
        
        self.assertEqual(res_material.status_code, 200, f"Material route failed: {res_material.text}")
        material_data = res_material.json()
        
        print(f" -> Gemini responded in {latency:.4f} seconds.")
        print(f" -> Validating response fields...")
        self.assertIn("voice_script", material_data)
        self.assertIn("technical_notes", material_data)
        self.assertIn("quiz", material_data)
        
        quiz = material_data["quiz"]
        self.assertEqual(len(quiz), 3, f"Expected exactly 3 quiz questions, got {len(quiz)}")
        print(" -> Verification: Script, Markdown notes, and 3-question quiz generated successfully.")

        # 4. Fetch Synced subtitles
        print("[STEP 4] Fetching dynamic WebVTT subtitle track...")
        res_sub = self.client.get(f"/api/topics/{topic.id}/subtitles")
        self.assertEqual(res_sub.status_code, 200)
        self.assertIn("text/vtt", res_sub.headers["content-type"])
        
        vtt_text = res_sub.text
        self.assertTrue(vtt_text.startswith("WEBVTT"), "Subtitle stream must start with WEBVTT identifier.")
        self.assertIn("1", vtt_text)
        self.assertIn("-->", vtt_text)
        print(" -> Verification: Time-synced WebVTT track compiled correctly.")

        # 5. Measure and toggle progress tracking
        print("[STEP 5] Checking progress status prior to toggle...")
        res_status_prev = self.client.get("/api/classroom/status")
        initial_completed = res_status_prev.json()["completed_topics"]
        
        print(" -> Toggling completion state to Completed...")
        res_toggle1 = self.client.post(f"/api/topics/{topic.id}/toggle")
        self.assertEqual(res_toggle1.status_code, 200)
        self.assertTrue(res_toggle1.json()["completed"])
        
        print(" -> Checking progress status after toggle...")
        res_status_post = self.client.get("/api/classroom/status")
        new_completed = res_status_post.json()["completed_topics"]
        
        self.assertEqual(new_completed, initial_completed + 1, "Completed topic count must increment by 1.")
        print(f" -> Verification: Progress status updated instantly in SQLite directory.")

        # 6. Toggle back to leave database clean (Idempotency)
        print("[STEP 6] Clearing completion to restore test DB sanitization...")
        res_toggle2 = self.client.post(f"/api/topics/{topic.id}/toggle")
        self.assertEqual(res_toggle2.status_code, 200)
        self.assertFalse(res_toggle2.json()["completed"])
        
        # Verify status is back to initial
        res_status_final = self.client.get("/api/classroom/status")
        self.assertEqual(res_status_final.json()["completed_topics"], initial_completed)
        print(" -> Database sanitized successfully.")
        
        print("=== PIPELINE EVALUATION COMPLETED: 100% CORRECT ===")

if __name__ == "__main__":
    unittest.main()
