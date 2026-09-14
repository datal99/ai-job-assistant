from pydantic import BaseModel, Field


class TailoredBullet(BaseModel):
    header: str
    content: str


class TailoredExperience(BaseModel):
    company: str
    position: str
    bullets: list[TailoredBullet]


class TailoredProject(BaseModel):
    name: str
    description: str


class TailoredSkills(BaseModel):
    programming: list[str]
    ai_and_agent_development: list[str]
    frameworks_and_technologies: list[str]
    software_engineering: list[str]
    databases: list[str]
    testing_and_quality: list[str]
    development_tools: list[str]
    cloud_and_architecture: list[str]
    development_practices: list[str]


class TailoredResume(BaseModel):
    summary: str = Field(
        description=(
            "Exactly three complete sentences and roughly 45 to 70 words. "
            "A natural professional introduction focused on the target role, "
            "not a keyword list."
        )
    )
    experience: list[TailoredExperience]
    projects: list[TailoredProject]
    technical_skills: TailoredSkills
