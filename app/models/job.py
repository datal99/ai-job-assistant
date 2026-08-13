from pydantic import BaseModel
from typing import List


class JobAnalysisResponse(BaseModel):
    match_score: int
    strong_matches: List[str]
    partial_matches: List[str]
    missing_skills: List[str]
    summary: str