from pydantic import BaseModel, Field


class ResumeValidationIssue(BaseModel):
    experience: str = Field(
        description="Company and position associated with the unsupported claim."
    )
    generated_bullet: str = Field(
        description="The generated bullet that is not fully supported."
    )
    reason: str = Field(
        description="A concise explanation of what the master resume does not support."
    )


class ResumeValidationResult(BaseModel):
    is_valid: bool = Field(
        description=(
            "True only when every generated employment bullet is fully supported "
            "by the master resume."
        )
    )
    issues: list[ResumeValidationIssue] = Field(
        description="Unsupported claims; empty when is_valid is true."
    )
