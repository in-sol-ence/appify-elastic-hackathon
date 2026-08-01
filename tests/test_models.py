from datetime import date

import pytest
from pydantic import ValidationError

from models.enums import EntityType, LogicType, Requiredness, SelectionStatus
from models.project import Capability, ProductSelection, Project, RequirementGroup
from services.templates import build_rover_template


def test_conditional_capability_requires_condition() -> None:
    with pytest.raises(ValidationError):
        Capability(name="Avoid obstacles", requiredness=Requiredness.CONDITIONAL)


def test_n_of_m_rejects_minimum_above_members() -> None:
    project = build_rover_template()
    with pytest.raises(ValidationError):
        RequirementGroup(
            group_name="Two sensors",
            owner_id=project.capabilities[0].id,
            owner_type=EntityType.CAPABILITY,
            logic_type=LogicType.N_OF_M,
            member_component_role_ids=[project.component_roles[0].id],
            minimum_required_count=2,
        )


def test_project_rejects_multiple_primary_products_per_role() -> None:
    project = build_rover_template()
    role_id = project.component_roles[0].id
    products = [
        ProductSelection(component_role_id=role_id, product_name="A", primary_product=True),
        ProductSelection(component_role_id=role_id, product_name="B", primary_product=True),
    ]
    with pytest.raises(ValidationError):
        Project.model_validate({**project.model_dump(), "products": [item.model_dump() for item in products]})


def test_rover_template_has_unique_milestone_sequences() -> None:
    project = build_rover_template()
    sequences = [item.sequence_number for item in project.milestones]
    assert len(sequences) == len(set(sequences))
    assert project.milestones[0].name == "Compute setup"
