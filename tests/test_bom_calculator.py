from models.enums import RoleRequiredness, SelectionStatus
from models.project import ProductSelection
from services.bom_calculator import bom_rows, calculate_bom_totals
from services.templates import build_sample_project


def test_bom_prices_quantities_and_budget() -> None:
    project=build_sample_project(); mandatory=project.component_roles[0]; optional=project.component_roles[-1]
    optional.requiredness=RoleRequiredness.OPTIONAL; project.total_budget=1500
    project.products=[
        ProductSelection(component_role_id=mandatory.id,product_name="Computer",quantity=2,expected_unit_price=100,primary_product=True,selection_status=SelectionStatus.SELECTED),
        ProductSelection(component_role_id=optional.id,product_name="Sensor",quantity=1,expected_unit_price=50,primary_product=True,selection_status=SelectionStatus.SELECTED),
    ]
    totals=calculate_bom_totals(project)
    assert totals.expected_total_cost==250
    assert totals.mandatory_cost==200
    assert totals.optional_cost==50
    assert totals.remaining_budget==1250
    assert totals.unresolved_prices==len(project.component_roles)-2
    assert next(row for row in bom_rows(project) if row["role_id"]==mandatory.id)["Expected total price"]==200


def test_missing_price_is_counted() -> None:
    project=build_sample_project(); role=project.component_roles[0]
    project.products=[ProductSelection(component_role_id=role.id,product_name="Unknown price",primary_product=True)]
    assert calculate_bom_totals(project).unresolved_prices==len(project.component_roles)
