from pydantic import BaseModel


class TailoredResume(BaseModel):
    summary: str
    experience: dict[str, list[str]]
    projects: dict[str, str]
    technical_skills: dict[str, list[str]]