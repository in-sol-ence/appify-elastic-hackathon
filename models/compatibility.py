from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


CompatibilityStatus = Literal["Compatible", "Potentially compatible", "Incompatible", "Insufficient information"]


class CompatibilityEvaluation(BaseModel):
    status: CompatibilityStatus
    passed_requirements: list[str] = Field(default_factory=list)
    failed_requirements: list[str] = Field(default_factory=list)
    unknown_requirements: list[str] = Field(default_factory=list)
    not_applicable_requirements: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ProductEvaluation(BaseModel):
    evaluation_id: str
    project_id: str
    component_role_id: str
    product_id: str
    compatibility_status: CompatibilityStatus
    hard_requirements_passed: list[str] = Field(default_factory=list)
    hard_requirements_failed: list[str] = Field(default_factory=list)
    unknown_requirements: list[str] = Field(default_factory=list)
    search_score: float = 0
    project_fit_score: float = 0
    failure_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
