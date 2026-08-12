import os

from dotenv import load_dotenv
from openai import OpenAI

from app.models import JobAnalysisResponse

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def analyze_job(prompt: str) -> JobAnalysisResponse:
    response = client.responses.parse(
        model="gpt-5-mini",
        input=prompt,
        text_format=JobAnalysisResponse
    )

    return response.output_parsed