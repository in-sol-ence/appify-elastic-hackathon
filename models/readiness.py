from pydantic import BaseModel, Field

from .enums import ReadinessStatus


class EntityReadiness(BaseModel):
    entity_id: str
    name: str
    status: ReadinessStatus
    reasons: list[str] = Field(default_factory=list)
    satisfied_requirements: int = 0
    unresolved_requirements: int = 0
    main_blocker: str | None = None


class ReadinessReport(BaseModel):
    status: ReadinessStatus
    reasons: list[str] = Field(default_factory=list)
    current_milestone_id: str | None = None
    component_roles: dict[str, EntityReadiness] = Field(default_factory=dict)
    requirement_groups: dict[str, EntityReadiness] = Field(default_factory=dict)
    capabilities: dict[str, EntityReadiness] = Field(default_factory=dict)
    milestones: dict[str, EntityReadiness] = Field(default_factory=dict)
    blockers: list[EntityReadiness] = Field(default_factory=list)
