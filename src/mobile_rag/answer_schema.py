"""Shared Pydantic answer contract for prompting and response validation."""

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator


class GroundedAnswer(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    status: Literal["answered", "insufficient_evidence"]
    answer: str
    reason: str = Field(min_length=1)
    citations: list[str]

    @field_validator("reason")
    @classmethod
    def nonblank_reason(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Reason must explain the evidence basis or missing support")
        return value

    @field_validator("citations")
    @classmethod
    def valid_citations(cls, labels: list[str], info: ValidationInfo) -> list[str]:
        if len(labels) != len(set(labels)):
            raise ValueError("Citation labels must be unique")
        if any(not label.strip() for label in labels):
            raise ValueError("Citation labels must not be blank")
        if info.context is not None and any(label not in info.context["citation_map"] for label in labels):
            raise ValueError("Unknown citation label")
        return labels

    @model_validator(mode="after")
    def consistent_outcome(self) -> Self:
        if self.status == "answered":
            if not self.answer.strip() or not self.citations:
                raise ValueError("Answered response requires answer text and citations")
        elif self.answer or self.citations:
            raise ValueError("Abstention requires an empty answer and citations")
        return self


def answer_json_schema(labels: list[str]) -> dict:
    """Generate the answer schema with request-specific citation labels."""
    if not labels or any(not isinstance(label, str) or not label.strip() for label in labels):
        raise ValueError("At least one nonblank citation label is required")
    schema = GroundedAnswer.model_json_schema()
    schema["properties"]["citations"]["items"]["enum"] = list(dict.fromkeys(labels))
    schema["properties"]["citations"]["uniqueItems"] = True
    schema["properties"]["reason"]["pattern"] = r"\S"
    schema["anyOf"] = [
        {"properties": {
            "status": {"const": "answered"},
            "answer": {"pattern": r"\S"},
            "citations": {"minItems": 1},
        }},
        {"properties": {
            "status": {"const": "insufficient_evidence"},
            "answer": {"const": ""},
            "citations": {"maxItems": 0},
        }},
    ]
    return schema
