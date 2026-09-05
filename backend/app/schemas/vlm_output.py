"""
VLM Output Schema — OmniSight Action Engine

This defines the exact JSON structure the ML team's Vision-Language Model (VLM)
must return after analyzing a UI screenshot. The backend's Action Engine (Week 2,
Day 2+) will parse and validate responses against this schema.

Contract agreed with ML team — any changes to field names/types here must be
communicated before ML builds their Day 2/3 prompt output.
"""

from pydantic import BaseModel, Field
from typing import Literal, Optional


class VLMBugReport(BaseModel):
    """
    Structure the VLM must return for each analyzed screenshot.
    """

    bug_found: bool = Field(
        ...,
        description="True if the VLM detected a visual UI issue, False if the screenshot looks clean."
    )

    description: Optional[str] = Field(
        None,
        description="Human-readable description of the bug. Required if bug_found is True."
    )

    fix: Optional[str] = Field(
        None,
        description="Suggested CSS/React code fix for the detected bug. Required if bug_found is True."
    )

    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="VLM's confidence in this detection/fix, 0.0 to 1.0. "
                    "Fixes below a threshold (e.g. 0.6) get flagged for human review instead of auto-merged."
    )

    severity_level: Optional[Literal["Critical", "Major", "Minor"]] = Field(
        None,
        description="Severity classification of the bug, for dashboard prioritization."
    )

    class Config:
        json_schema_extra = {
            "example": {
                "bug_found": True,
                "description": "Checkout button is clipped outside the mobile viewport",
                "fix": "Add 'overflow-x: hidden' to the container and set button width to 90%",
                "confidence_score": 0.87,
                "severity_level": "Major"
            }
        }