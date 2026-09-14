from pydantic import BaseModel, ConfigDict, Field


class JobPosting(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    company: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=50_000)
