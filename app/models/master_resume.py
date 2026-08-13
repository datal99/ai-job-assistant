from pydantic import BaseModel


class MasterExperience(BaseModel):
    company: str
    location: str
    position: str
    dates: str


class MasterResume(BaseModel):
    experience: list[MasterExperience]