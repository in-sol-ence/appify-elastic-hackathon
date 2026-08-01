from dataclasses import dataclass

from models.enums import RoleRequiredness, SelectionStatus
from models.project import Project
from models.readiness import ReadinessReport


@dataclass(frozen=True)
class BomTotals:
    expected_total_cost: float
    selected_product_cost: float
    mandatory_cost: float
    optional_cost: float
    remaining_budget: float
    unresolved_prices: int


def selected_product(project: Project, role_id: str):
    products = [p for p in project.products if p.component_role_id == role_id]
    return next((p for p in products if p.primary_product), None) or next((p for p in products if p.selection_status == SelectionStatus.SELECTED), None)


def bom_rows(project: Project, readiness: ReadinessReport | None = None) -> list[dict]:
    names = project.entity_names()
    rows = []
    for role in project.component_roles:
        product = selected_product(project, role.id)
        qty = product.quantity if product else role.required_quantity
        price = product.expected_unit_price if product else 0
        rows.append({
            "role_id": role.id, "Component role": role.role_name, "Category": role.category,
            "Capability": names.get(role.capability_id, "Not assigned"), "Required quantity": role.required_quantity,
            "Requiredness": role.requiredness.value, "Required milestone": names.get(role.first_required_milestone_id, "Not assigned"),
            "Selected product": product.product_name if product else "Not selected", "Product quantity": qty,
            "Expected unit price": price, "Expected total price": qty * price,
            "Role status": role.current_status.value,
            "Purchase status": product.purchase_status.value if product else "Not planned",
            "Verification status": product.verification_status.value if product else "Unverified",
            "Readiness status": readiness.component_roles[role.id].status.value if readiness and role.id in readiness.component_roles else "Not evaluated",
        })
    return rows


def calculate_bom_totals(project: Project) -> BomTotals:
    total = mandatory = optional = selected_cost = 0.0
    unresolved = 0
    for role in project.component_roles:
        product = selected_product(project, role.id)
        if not product or product.expected_unit_price <= 0:
            unresolved += 1
            continue
        cost = product.quantity * product.expected_unit_price
        total += cost
        selected_cost += cost
        if role.requiredness in {RoleRequiredness.MANDATORY, RoleRequiredness.CONDITIONAL}:
            mandatory += cost
        else:
            optional += cost
    return BomTotals(total, selected_cost, mandatory, optional, project.total_budget-total, unresolved)
