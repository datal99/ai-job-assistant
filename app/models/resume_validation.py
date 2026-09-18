from typing import Literal

from pydantic import BaseModel, Field


class ResumeValidationIssue(BaseModel):
    section: Literal["experience", "projects"] = Field(
        description="Resume section containing the unsupported claim or omission."
    )
    item: str = Field(
        description="Employer and position, or project name, affected by the issue."
    )
    generated_text: str = Field(
        description=(
            "Unsupported generated text, or an empty string for a material omission."
        )
    )
    reason: str = Field(
        description="A concise explanation of the unsupported claim or omission."
    )


class ResumeValidationResult(BaseModel):
    is_valid: bool = Field(
        description=(
            "True only when every generated employment bullet is fully supported "
            "and the tailored content preserves material relevant evidence."
        )
    )
    issues: list[ResumeValidationIssue] = Field(
        description="Unsupported claims or material omissions; empty when valid."
    )
