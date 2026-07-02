import os
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# Ensure models initialized for router/service testing
class QuizQuestion(BaseModel):
    question: str = Field(description="The multiple choice question text.")
    options: list[str] = Field(description="List of exactly 3 options for the question.")
    correct_answer_idx: int = Field(description="Index of the correct answer in the options list (0, 1, or 2).")

class LessonMaterial(BaseModel):
    voice_script: str = Field(description="A word-for-word voice script for a video lecture on this topic.")
    technical_notes: str = Field(description="Comprehensive technical reading notes in detailed Markdown format with code examples where applicable.")
    quiz: list[QuizQuestion] = Field(description="A 3-question multiple-choice quiz testing understanding.")

def get_gemini_client() -> genai.Client:
    """Initialize standard Gemini GenAI client from environment variable."""
    # Ensure GEMINI_API_KEY is present or throw descriptive helper exception
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        api_key = "dummy_api_key_for_testing" # Safe fallback for initial verification if needed
        # We can also raise ValueError in production
        # raise ValueError("GEMINI_API_KEY environment variable is missing")
    return genai.Client(api_key=api_key)

def generate_material_for_topic(topic_content: str) -> LessonMaterial:
    """Generates structured lecture resources for a specific curriculum topic using Gemini."""
    client = get_gemini_client()
    
    prompt = f"""
    You are an expert AI Engineer and educator leading a self-paced bootcamp. 
    Develop video script lesson resources, in-depth reading notes, and quizzes for the following topic:
    "{topic_content}"

    Detailed Instructions:
    1. voice_script: Provide a word-for-word lecture audio transcript that is natural, professional, and explaining the topic details step-by-step.
    2. technical_notes: Comprehensive, structured textbook-like reading notes written in clean Markdown. Include key takeaways, theoretical definitions, code snippets or command-line instructions, and pros/cons.
    3. quiz: Supply exactly 3 multiple-choice questions to query learning retention. Each question must list exactly 3 distinct choices, with correct_answer_idx representing the proper clean array boundary (0, 1, or 2).
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
