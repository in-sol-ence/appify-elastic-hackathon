from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


class Product(BaseModel):
    product_id: str
    manufacturer: str
    name: str
    model: str = ""
    manufacturer_part_number: str = ""
    category: str
    subcategory: str = ""
    description: str = ""
    product_summary: str = ""
    intended_applications: list[str] = Field(default_factory=list)
    important_features: list[str] = Field(default_factory=list)
    motor_types: list[str] = Field(default_factory=list)
    control_interfaces: list[str] = Field(default_factory=list)
    communication_interfaces: list[str] = Field(default_factory=list)
    supported_operating_systems: list[str] = Field(default_factory=list)
    supported_software: list[str] = Field(default_factory=list)
    input_voltage_min_v: float | None = None
    input_voltage_max_v: float | None = None
    continuous_current_a: float | None = None
    continuous_current_per_channel_a: float | None = None
    peak_current_a: float | None = None
    peak_current_per_channel_a: float | None = None
    channel_count: int | None = None
    power_w: float | None = None
    weight_g: float | None = None
    length_mm: float | None = None
    width_mm: float | None = None
    height_mm: float | None = None
    price_estimate: float | None = None
    currency: str | None = None
    documentation_available: bool | None = None
    lifecycle_status: str = "unknown"
    specification_confidence: float = Field(default=0.5, ge=0, le=1)
    source_type: str = "development_sample"
    source_url: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def semantic_content(self) -> str:
        values = [self.name, self.category, self.product_summary, *self.intended_applications, *self.important_features]
        return ". ".join(value for value in values if value)


class ProductEvidence(BaseModel):
    evidence_id: str
    product_id: str
    manufacturer: str = ""
    product_model: str = ""
    source_type: str
    title: str
    text: str
    semantic_text: str = ""
    hardware_revision: str = ""
    firmware_version: str = ""
    operating_system: str = ""
    software_version: str = ""
    published_at: datetime | None = None
    collected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_authority: float = Field(default=0.5, ge=0, le=1)
    source_url: str = ""


class EvidenceFilters(BaseModel):
    source_type: str | None = None
    hardware_revision: str | None = None
    firmware_version: str | None = None
    operating_system: str | None = None
    software_version: str | None = None
    minimum_source_authority: float | None = None
    published_after: datetime | None = None
