from pydantic import BaseModel


class JobPosting(BaseModel):
    company: str
    title: str
    description: str