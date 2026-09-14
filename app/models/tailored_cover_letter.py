from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


CoverLetterParagraph = Annotated[str, Field(min_length=20, max_length=2_000)]


class TailoredCoverLetter(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    paragraphs: list[CoverLetterParagraph] = Field(min_length=3, max_length=5)
