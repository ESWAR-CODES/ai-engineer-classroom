import os
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

class QuizQuestion(BaseModel):
    question: str = Field(description="The multiple choice question text.")
    options: list[str] = Field(description="List of exactly 3 options for the question.")
    correct_answer_idx: int = Field(description="Index of the correct answer in the options list (0, 1, or 2).")

class LessonMaterial(BaseModel):
    technical_notes: str = Field(description="Comprehensive technical reading notes in detailed Markdown format with code examples where applicable.")
    quiz: list[QuizQuestion] = Field(description="A 3-question multiple-choice quiz testing understanding.")

def get_gemini_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        api_key = "dummy_api_key_for_testing"
    return genai.Client(api_key=api_key)

def generate_material_for_topic(topic_content: str) -> LessonMaterial:
    client = get_gemini_client()
    prompt = f"""
    You are an expert AI Engineer and educator leading a self-paced bootcamp. 
    Develop in-depth reading notes and quizzes for the following topic:
    "{topic_content}"

    Detailed Instructions:
    1. technical_notes: Comprehensive, structured textbook-like reading notes written in clean Markdown. Include key takeaways, theoretical definitions, code snippets or command-line instructions, and pros/cons.
    2. quiz: Supply exactly 3 multiple-choice questions to query learning retention. Each question must list exactly 3 distinct choices, with correct_answer_idx representing the proper clean array boundary (0, 1, or 2).
    """
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=LessonMaterial,
        ),
    )
    return LessonMaterial.model_validate_json(response.text)
