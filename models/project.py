from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .enums import (
    EntityType, FindingSeverity, LogicType, OperatingEnvironment, ProjectStage,
    PurchaseStatus, RelationshipType, RelationshipValidationStatus,
    RequirementStrength, Requiredness, RiskTolerance, RoleRequiredness,
    RoleStatus, SelectionStatus, Strength, VerificationStatus,
)


def new_id() -> str:
    return str(uuid4())


class DomainModel(BaseModel):
    model_config = ConfigDict(use_enum_values=False, validate_assignment=False)


class Milestone(DomainModel):
    id: str = Field(default_factory=new_id)
    name: str
    description: str = ""
    sequence_number: int = Field(ge=1)
    target_date: date
    mandatory: bool = True
    completion_criteria: str = ""
    completed: bool = False

    @field_validator("id")
    @classmethod
    def valid_id(cls, value: str) -> str:
        UUID(value)
        return value


class Capability(DomainModel):
    id: str = Field(default_factory=new_id)
    name: str
    description: str = ""
    requiredness: Requiredness = Requiredness.MANDATORY
    first_relevant_milestone_id: str | None = None
    acceptance_criteria: str = ""
    condition_description: str | None = None

    @model_validator(mode="after")
    def conditional_has_condition(self) -> Capability:
        if self.requiredness == Requiredness.CONDITIONAL and not (self.condition_description or "").strip():
            raise ValueError("Conditional capabilities require a condition description")
        return self


class ComponentRole(DomainModel):
    id: str = Field(default_factory=new_id)
    role_name: str
    category: str
    purpose: str = ""
    capability_id: str | None = None
    required_quantity: int = Field(default=1, ge=1)
    requiredness: RoleRequiredness = RoleRequiredness.MANDATORY
    first_required_milestone_id: str | None = None
    required_by: date | None = None
    necessity_confidence: int = Field(default=100, ge=0, le=100)
    replacement_difficulty: int = Field(default=3, ge=1, le=5)
    integration_risk: int = Field(default=3, ge=1, le=5)
    functional_acceptance_criteria: str = ""
    acceptance_requirements: dict[str, str] = Field(default_factory=dict)
    current_status: RoleStatus = RoleStatus.PROPOSED
    condition_description: str | None = None
    condition_active: bool | None = None

    @model_validator(mode="after")
    def conditional_has_condition(self) -> ComponentRole:
        if self.requiredness == RoleRequiredness.CONDITIONAL and not (self.condition_description or "").strip():
            raise ValueError("Conditional component roles require a condition description")
        return self


class RoleMilestoneRating(DomainModel):
    component_role_id: str
    milestone_id: str
    rating: int = Field(ge=0, le=5)


class ProductSelection(DomainModel):
    id: str = Field(default_factory=new_id)
    component_role_id: str
    manufacturer: str = ""
    product_name: str
    model: str = ""
    manufacturer_part_number: str = ""
    quantity: int = Field(default=1, ge=1)
    expected_unit_price: float = Field(default=0, ge=0)
    supplier_name: str = ""
    supplier_url: str = ""
    manufacturer_url: str = ""
    hardware_revision: str = ""
    firmware_version: str = ""
    selection_status: SelectionStatus = SelectionStatus.CANDIDATE
    purchase_status: PurchaseStatus = PurchaseStatus.NOT_PLANNED
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    primary_product: bool = False
    alternatives_allowed: bool = True
    notes: str = ""
    elastic_product_id: str | None = None
    catalog_specs: dict[str, Any] = Field(default_factory=dict)
    rejection_reason: str | None = None
    rejected_at: datetime | None = None


class Relationship(DomainModel):
    id: str = Field(default_factory=new_id)
    source_id: str
    source_type: EntityType
    relationship_type: RelationshipType
    target_id: str
    target_type: EntityType
    strength: Strength = Strength.HARD
    relevant_milestone_id: str | None = None
    condition: str = ""
    notes: str = ""
    validation_status: RelationshipValidationStatus = RelationshipValidationStatus.UNVERIFIED

    @model_validator(mode="after")
    def no_self_reference(self) -> Relationship:
        if self.source_id == self.target_id:
            raise ValueError("A relationship cannot use the same source and target")
        return self


class RequirementGroup(DomainModel):
    id: str = Field(default_factory=new_id)
    group_name: str
    owner_id: str
    owner_type: EntityType
    logic_type: LogicType
    member_component_role_ids: list[str] = Field(default_factory=list)
    requirement_strength: RequirementStrength = RequirementStrength.HARD
    relevant_milestone_id: str | None = None
    condition: str = ""
    condition_active: bool | None = None
    minimum_required_count: int | None = None

    @model_validator(mode="after")
    def valid_n_of_m(self) -> RequirementGroup:
        if self.logic_type == LogicType.N_OF_M:
            if self.minimum_required_count is None or self.minimum_required_count <= 0:
                raise ValueError("N_OF_M minimum must be greater than zero")
            if self.minimum_required_count > len(self.member_component_role_ids):
                raise ValueError("N_OF_M minimum cannot exceed its member count")
        return self


class ValidationFinding(DomainModel):
    severity: FindingSeverity
    code: str
    message: str
    entity_id: str | None = None
    entity_type: str | None = None
    title: str = ""
    suggested_correction: str = ""


class Project(DomainModel):
    id: str = Field(default_factory=new_id)
    name: str = ""
    short_description: str = ""
    total_budget: float = Field(default=0, ge=0)
    final_deadline: date | None = None
    current_stage: ProjectStage = ProjectStage.CONCEPT
    operating_environment: OperatingEnvironment = OperatingEnvironment.UNKNOWN
    location: str = ""
    software_platform: str = ""
    team_size: int = Field(default=1, ge=1)
    risk_tolerance: RiskTolerance = RiskTolerance.MODERATE
    milestones: list[Milestone] = Field(default_factory=list)
    capabilities: list[Capability] = Field(default_factory=list)
    component_roles: list[ComponentRole] = Field(default_factory=list)
    role_milestone_ratings: list[RoleMilestoneRating] = Field(default_factory=list)
    products: list[ProductSelection] = Field(default_factory=list)
    relationships: list[Relationship] = Field(default_factory=list)
    requirement_groups: list[RequirementGroup] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def project_rules(self) -> Project:
        primary_counts: dict[str, int] = {}
        for product in self.products:
            if product.primary_product:
                primary_counts[product.component_role_id] = primary_counts.get(product.component_role_id, 0) + 1
        duplicates = [role_id for role_id, count in primary_counts.items() if count > 1]
        if duplicates:
            raise ValueError("Only one product per component role may be primary")
        return self

    def entity_names(self) -> dict[str, str]:
        result = {self.id: self.name or "Untitled project"}
        result.update({item.id: item.name for item in self.milestones})
        result.update({item.id: item.name for item in self.capabilities})
        result.update({item.id: item.role_name for item in self.component_roles})
        result.update({item.id: item.product_name for item in self.products})
        result.update({item.id: item.group_name for item in self.requirement_groups})
        return result

    def as_json(self) -> str:
        return self.model_dump_json(indent=2)
