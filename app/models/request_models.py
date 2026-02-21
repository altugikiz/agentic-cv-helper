"""Request models for the Career Assistant API."""

from pydantic import BaseModel, Field


class MessageRequest(BaseModel):
    """Incoming employer message."""

    sender: str = Field(
        ...,
        description="Sender identifier (e-mail, name, or company)",
        examples=["hr@company.com"],
    )
    message: str = Field(
        ...,
        description="The employer's message text",
        examples=["We'd like to invite you for a technical interview next Tuesday."],
    )


class TestRequest(BaseModel):
    """Request to run a predefined test scenario."""

    test_id: str = Field(
        ...,
        description="Identifier of the test scenario to execute",
        examples=["test_interview_invitation"],
    )
