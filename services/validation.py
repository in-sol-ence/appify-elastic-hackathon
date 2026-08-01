from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from models.enums import (
    FindingSeverity, LogicType, PurchaseStatus, RoleRequiredness, RoleStatus,
    SelectionStatus, VerificationStatus,
)
from models.project import Project, ValidationFinding


def finding(severity: FindingSeverity, code: str, message: str, entity_id: str | None = None, entity_type: str | None = None, title: str = "", correction: str = "") -> ValidationFinding:
    return ValidationFinding(severity=severity, code=code, message=message, entity_id=entity_id, entity_type=entity_type, title=title or code.replace("_", " ").title(), suggested_correction=correction)


def _cycles(project: Project) -> list[list[str]]:
    valid_ids = set(project.entity_names())
    edges: dict[str, list[str]] = defaultdict(list)
    for relationship in project.relationships:
        if relationship.source_id in valid_ids and relationship.target_id in valid_ids:
            edges[relationship.source_id].append(relationship.target_id)
    visiting: set[str] = set()
    visited: set[str] = set()
    stack: list[str] = []
    found: list[list[str]] = []

    def visit(node: str) -> None:
        if node in visiting:
            start = stack.index(node)
            cycle = stack[start:] + [node]
            if cycle not in found:
                found.append(cycle)
            return
        if node in visited:
            return
        visiting.add(node)
        stack.append(node)
        for target in edges[node]:
            visit(target)
        stack.pop()
        visiting.remove(node)
        visited.add(node)

    for node in valid_ids:
        visit(node)
    return found


def validate_project(project: Project) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    milestones = {item.id: item for item in project.milestones}
    capabilities = {item.id: item for item in project.capabilities}
    roles = {item.id: item for item in project.component_roles}
    products = {item.id: item for item in project.products}
    all_entities = {**milestones, **capabilities, **roles, **products}
    names = project.entity_names()
    all_ids = [project.id, *milestones, *capabilities, *roles, *products, *(item.id for item in project.relationships), *(item.id for item in project.requirement_groups)]
    if len(all_ids) != len(set(all_ids)):
        findings.append(finding(FindingSeverity.BLOCKING, "duplicate_entity_ids", "Entity IDs must be unique across the project.", correction="Regenerate duplicate entity IDs and repair references."))

    if not project.name.strip():
        findings.append(finding(FindingSeverity.BLOCKING, "missing_project_name", "Project name is required.", project.id))
    if not project.milestones:
        findings.append(finding(FindingSeverity.BLOCKING, "no_milestones", "At least one milestone is required.", project.id))
    milestone_names = [item.name.strip().lower() for item in project.milestones]
    if any(not name for name in milestone_names):
        findings.append(finding(FindingSeverity.BLOCKING, "empty_milestone_name", "Milestone names cannot be empty."))
    sequences = [item.sequence_number for item in project.milestones]
    if len(sequences) != len(set(sequences)):
        findings.append(finding(FindingSeverity.BLOCKING, "duplicate_milestone_sequence", "Milestone sequence numbers must be unique."))
    if project.final_deadline:
        for milestone in project.milestones:
            if milestone.target_date > project.final_deadline:
                findings.append(finding(FindingSeverity.BLOCKING, "milestone_after_deadline", f"{milestone.name} occurs after the final project deadline.", milestone.id))

    for capability in project.capabilities:
        if capability.first_relevant_milestone_id and capability.first_relevant_milestone_id not in milestones:
            findings.append(finding(FindingSeverity.BLOCKING, "capability_deleted_milestone", f"{capability.name} references a milestone that no longer exists.", capability.id))

    for role in project.component_roles:
        if role.capability_id and role.capability_id not in capabilities:
            findings.append(finding(FindingSeverity.BLOCKING, "role_deleted_capability", f"{role.role_name} references a capability that no longer exists.", role.id))
        if not role.capability_id:
            findings.append(finding(FindingSeverity.WARNING, "role_no_capability", f"{role.role_name} is not connected to a capability.", role.id))
        if role.first_required_milestone_id and role.first_required_milestone_id not in milestones:
            findings.append(finding(FindingSeverity.BLOCKING, "role_deleted_milestone", f"{role.role_name} references a milestone that no longer exists.", role.id))
        if role.requiredness == RoleRequiredness.MANDATORY and not role.first_required_milestone_id:
            findings.append(finding(FindingSeverity.BLOCKING, "mandatory_role_no_milestone", f"Mandatory component {role.role_name} has no first required milestone.", role.id))
        if role.requiredness in {RoleRequiredness.MANDATORY, RoleRequiredness.CONDITIONAL} and role.necessity_confidence < 50:
            findings.append(finding(FindingSeverity.WARNING, "required_low_confidence", f"Required role {role.role_name} has necessity confidence below 50 percent.", role.id))
        if (
            role.requiredness == RoleRequiredness.MANDATORY
            and role.required_by
            and role.required_by <= date.today() + timedelta(days=30)
            and role.current_status not in {RoleStatus.ORDERED, RoleStatus.RECEIVED, RoleStatus.INSPECTED, RoleStatus.VERIFIED, RoleStatus.INTEGRATED, RoleStatus.SYSTEM_TESTED}
        ):
            findings.append(finding(FindingSeverity.WARNING, "required_soon_not_ordered", f"{role.role_name} is required by {role.required_by.isoformat()} but is not ordered or received.", role.id))

    primary_by_role: dict[str, int] = defaultdict(int)
    for product in project.products:
        if product.component_role_id not in roles:
            findings.append(finding(FindingSeverity.BLOCKING, "product_no_role", f"Product {product.product_name} has no valid component role.", product.id))
        if product.primary_product:
            primary_by_role[product.component_role_id] += 1
        if product.selection_status == SelectionStatus.SELECTED and product.verification_status == VerificationStatus.UNVERIFIED:
            findings.append(finding(FindingSeverity.WARNING, "selected_unverified", f"Selected product {product.product_name} is still unverified.", product.id, "Product", correction="Review specifications or bench test the product."))
        if product.expected_unit_price <= 0:
            findings.append(finding(FindingSeverity.WARNING, "missing_expected_price", f"{product.product_name} has no expected unit price.", product.id, "Product", correction="Enter an estimated unit price."))
    for role_id, count in primary_by_role.items():
        if count > 1:
            findings.append(finding(FindingSeverity.BLOCKING, "multiple_primary", f"{names.get(role_id, 'A component role')} has more than one primary product.", role_id))

    for group in project.requirement_groups:
        if not group.member_component_role_ids:
            findings.append(finding(FindingSeverity.BLOCKING, "empty_requirement_group", f"Requirement group {group.group_name} has no members.", group.id))
        missing = [member_id for member_id in group.member_component_role_ids if member_id not in roles]
        if missing:
            findings.append(finding(FindingSeverity.BLOCKING, "group_deleted_member", f"Requirement group {group.group_name} references {len(missing)} deleted component role(s).", group.id))
        if group.logic_type == LogicType.N_OF_M:
            minimum = group.minimum_required_count or 0
            if minimum <= 0 or minimum > len(group.member_component_role_ids):
                findings.append(finding(FindingSeverity.BLOCKING, "invalid_n_of_m", f"{group.group_name} has an invalid N_OF_M minimum.", group.id))

    for relationship in project.relationships:
        if relationship.source_id == relationship.target_id:
            findings.append(finding(FindingSeverity.BLOCKING, "self_dependency", "A dependency cannot reference the same source and target.", relationship.id))
        if relationship.source_id not in all_entities or relationship.target_id not in all_entities:
            findings.append(finding(FindingSeverity.BLOCKING, "deleted_dependency_entity", "A dependency references an entity that no longer exists.", relationship.id))
        if relationship.relevant_milestone_id and relationship.relevant_milestone_id not in milestones:
            findings.append(finding(FindingSeverity.WARNING, "dependency_deleted_milestone", "A dependency references a deleted milestone.", relationship.id))

    for cycle in _cycles(project):
        label = " → ".join(names.get(item, "Unknown") for item in cycle)
        findings.append(finding(FindingSeverity.WARNING, "circular_dependency", f"Circular dependency detected: {label}. Review whether this is intentional."))

    active_roles = [role for role in project.component_roles if role.current_status != RoleStatus.REMOVED]
    motor_roles = [role for role in active_roles if "motor" in role.role_name.lower() and "driver" not in role.role_name.lower()]
    driver_roles = [role for role in active_roles if "motor driver" in role.role_name.lower()]
    mobility_present = any(role.category.lower() == "mobility" for role in active_roles)
    selected_statuses = {RoleStatus.SELECTED, RoleStatus.ORDERED, RoleStatus.RECEIVED, RoleStatus.INSPECTED, RoleStatus.VERIFIED, RoleStatus.INTEGRATED, RoleStatus.SYSTEM_TESTED}
    selected_drivers = [role for role in driver_roles if role.current_status in selected_statuses]
    selected_motors = [role for role in motor_roles if role.current_status in selected_statuses]
    if mobility_present and not driver_roles:
        findings.append(finding(FindingSeverity.BLOCKING, "mobility_no_driver", "Manual mobility is blocked because mobility components are present but no Motor driver role exists."))
    elif motor_roles and not selected_drivers:
        findings.append(finding(FindingSeverity.WARNING, "mobility_driver_not_selected", "Manual mobility is blocked because the Drive motor requires a compatible Motor driver, but no motor driver has been selected."))
    if driver_roles and not motor_roles:
        findings.append(finding(FindingSeverity.BLOCKING, "driver_no_motor", "A Motor driver is present, but no drive motor role exists."))
    elif selected_drivers and not selected_motors:
        findings.append(finding(FindingSeverity.WARNING, "driver_motor_not_selected", "The Motor driver is selected, but no compatible motor has been selected."))

    selected_role_ids = {product.component_role_id for product in project.products if product.primary_product or product.selection_status == SelectionStatus.SELECTED}
    for role in active_roles:
        if role.requiredness == RoleRequiredness.MANDATORY and role.id not in selected_role_ids:
            findings.append(finding(FindingSeverity.WARNING, "mandatory_role_no_product", f"Mandatory role {role.role_name} has no selected product.", role.id, "Component role", correction="Select or mark a primary product."))
        milestone = milestones.get(role.first_required_milestone_id)
        if role.required_by and role.required_by < project.created_at.date():
            findings.append(finding(FindingSeverity.WARNING, "required_before_creation", f"{role.role_name} is required before the project creation date.", role.id))
        if role.required_by and milestone and role.required_by > milestone.target_date:
            findings.append(finding(FindingSeverity.WARNING, "required_after_milestone", f"{role.role_name} is required after its milestone target date.", role.id))
    selected_product_ids = {p.id for p in project.products if p.primary_product or p.selection_status == SelectionStatus.SELECTED}
    for relationship in project.relationships:
        if relationship.relationship_type.value == "Incompatible with" and relationship.source_id in selected_product_ids and relationship.target_id in selected_product_ids:
            findings.append(finding(FindingSeverity.BLOCKING, "selected_incompatible_products", "Two selected products are explicitly incompatible.", relationship.id, "Relationship", correction="Choose a compatible alternative or remove one selection."))
    compute = any("compute" in r.category.lower() or "computer" in r.role_name.lower() for r in active_roles)
    power = any("power" in r.category.lower() or "battery" in r.role_name.lower() or "converter" in r.role_name.lower() for r in active_roles)
    if compute and not power:
        findings.append(finding(FindingSeverity.WARNING, "compute_without_power", "Compute hardware has no power-source or converter role."))
    sensors = [r for r in active_roles if "sensor" in r.role_name.lower() or r.category.lower() == "sensing"]
    controllers = [r for r in active_roles if "computer" in r.role_name.lower() or "controller" in r.role_name.lower()]
    if sensors and not controllers:
        findings.append(finding(FindingSeverity.WARNING, "sensor_without_controller", "Sensor roles exist without a computer or controller role."))

    if not findings:
        findings.append(finding(FindingSeverity.INFORMATIONAL, "validation_passed", "No validation problems were found."))
    return findings


def validate_step(project: Project, step: int) -> list[ValidationFinding]:
    findings = validate_project(project)
    codes_by_step = {
        1: set(),
        2: {"missing_project_name"},
        3: {"no_milestones", "empty_milestone_name", "duplicate_milestone_sequence", "milestone_after_deadline"},
        4: {"capability_deleted_milestone"},
        5: {"role_deleted_capability", "role_deleted_milestone", "mandatory_role_no_milestone"},
        6: set(),
        7: {"self_dependency", "deleted_dependency_entity"},
        8: {"empty_requirement_group", "group_deleted_member", "invalid_n_of_m"},
        9: {"product_no_role", "multiple_primary"},
    }
    selected = [item for item in findings if item.code in codes_by_step.get(step, set())]
    if step == 2:
        if project.final_deadline is None:
            selected.append(finding(FindingSeverity.BLOCKING, "missing_deadline", "Final deadline is required."))
        if not project.short_description.strip():
            selected.append(finding(FindingSeverity.BLOCKING, "missing_description", "Short description is required."))
    return selected


def has_blocking(findings: list[ValidationFinding]) -> bool:
    return any(item.severity == FindingSeverity.BLOCKING for item in findings)
