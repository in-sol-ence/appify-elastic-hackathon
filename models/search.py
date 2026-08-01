from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field

from .products import Product


class CompatibilityRequirement(BaseModel):
    field: str
    operator: Literal["eq", "contains_any", "lte", "gte", "range_includes", "exists"]
    value: Any
    hard: bool = True
    description: str


class ComponentSearchProfile(BaseModel):
    project_id: str
    component_role_id: str
    role_name: str
    category: str
    purpose: str
    required_quantity: int
    required_milestone: str | None = None
    required_by_date: date | None = None
    criticality: int = 0
    necessity_confidence: int
    project_budget: float
    component_budget: float | None = None
    hard_requirements: list[CompatibilityRequirement] = Field(default_factory=list)
    preferred_requirements: list[CompatibilityRequirement] = Field(default_factory=list)
    connected_components: list[str] = Field(default_factory=list)
    software_platform: str = ""
    operating_environment: str = ""
    natural_language_description: str


class ProductSearchRequest(BaseModel):
    profile: ComponentSearchProfile
    query: str = ""
    limit: int = Field(default=20, ge=1, le=100)


class ProductSearchResult(BaseModel):
    product: Product
    search_score: float = 0
    project_fit_score: float = 0
    compatibility_status: str = "Insufficient information"
    matched_requirements: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    search_explanation: str = ""
    score_explanation: dict[str, float] = Field(default_factory=dict)
