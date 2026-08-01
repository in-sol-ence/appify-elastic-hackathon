from dataclasses import dataclass
from datetime import date, timedelta

from models.enums import (
    LogicType, ReadinessStatus, RelationshipType, RelationshipValidationStatus,
    RequirementStrength, Requiredness, RoleRequiredness, RoleStatus,
    SelectionStatus, VerificationStatus,
)
from models.project import Project, RequirementGroup
from models.readiness import EntityReadiness, ReadinessReport


@dataclass(frozen=True)
class ReadinessResult:
    owner_id: str
    owner_name: str
    status: ReadinessStatus
    reason: str


COMPLETE_STATUSES = {RoleStatus.VERIFIED, RoleStatus.INTEGRATED, RoleStatus.SYSTEM_TESTED}
PROGRESS_STATUSES = {RoleStatus.SELECTED, RoleStatus.ORDERED, RoleStatus.RECEIVED, RoleStatus.INSPECTED, *COMPLETE_STATUSES}
VERIFIED_PRODUCTS = {VerificationStatus.SPEC_REVIEWED, VerificationStatus.BENCH_TESTED, VerificationStatus.INTEGRATED}


def _selected_products(project: Project, role_id: str):
    products = [p for p in project.products if p.component_role_id == role_id]
    primary = [p for p in products if p.primary_product]
    selected = [p for p in products if p.selection_status == SelectionStatus.SELECTED]
    return primary or selected


def _condition_state(requiredness, active: bool | None) -> bool | None:
    if requiredness not in {RoleRequiredness.CONDITIONAL, Requiredness.CONDITIONAL}:
        return True
    return active


def evaluate_group(project: Project, group: RequirementGroup) -> ReadinessResult:
    """Compatibility API used by existing callers; full reports use evaluate_project_readiness."""
    names = project.entity_names()
    roles = {r.id: r for r in project.component_roles if r.current_status != RoleStatus.REMOVED}
    members = [roles.get(role_id) for role_id in group.member_component_role_ids]
    present = sum(m is not None and m.current_status in PROGRESS_STATUSES for m in members)
    complete = sum(m is not None and m.current_status in COMPLETE_STATUSES for m in members)
    needed = len(group.member_component_role_ids) if group.logic_type == LogicType.ALL_OF else (1 if group.logic_type == LogicType.ANY_OF else group.minimum_required_count or 0)
    owner = names.get(group.owner_id, "Deleted owner")
    if group.condition and group.condition_active is False:
        return ReadinessResult(group.owner_id, owner, ReadinessStatus.NOT_EVALUATED, "Conditional requirement is disabled.")
    if not group.member_component_role_ids:
        return ReadinessResult(group.owner_id, owner, ReadinessStatus.BLOCKED, f"{group.group_name} has no members.")
    if complete >= needed:
        return ReadinessResult(group.owner_id, owner, ReadinessStatus.READY, f"{complete} verified member(s) satisfy {group.logic_type.value}.")
    if present >= needed:
        return ReadinessResult(group.owner_id, owner, ReadinessStatus.AT_RISK, "Required items exist but are not all verified or integrated.")
    status = ReadinessStatus.BLOCKED if group.requirement_strength == RequirementStrength.HARD else ReadinessStatus.AT_RISK
    return ReadinessResult(group.owner_id, owner, status, f"Only {present} of {needed} required member(s) are selected or available.")


def _role_readiness(project: Project) -> dict[str, EntityReadiness]:
    result: dict[str, EntityReadiness] = {}
    selected_product_ids = {p.id for role in project.component_roles for p in _selected_products(project, role.id)}
    for role in project.component_roles:
        reasons: list[str] = []
        if role.requiredness == RoleRequiredness.REMOVED or role.current_status == RoleStatus.REMOVED:
            result[role.id] = EntityReadiness(entity_id=role.id, name=role.role_name, status=ReadinessStatus.NOT_EVALUATED, reasons=["Role is removed."])
            continue
        condition = _condition_state(role.requiredness, role.condition_active)
        if condition is False:
            result[role.id] = EntityReadiness(entity_id=role.id, name=role.role_name, status=ReadinessStatus.NOT_EVALUATED, reasons=["Conditional role is disabled."])
            continue
        products = _selected_products(project, role.id)
        required = role.requiredness in {RoleRequiredness.MANDATORY, RoleRequiredness.CONDITIONAL}
        blocked = False
        if required and not products:
            reasons.append(f"No selected product fills {role.role_name}.")
            blocked = True
        if condition is None:
            reasons.append("The conditional requirement has not been evaluated.")
        if products:
            if any(p.verification_status == VerificationStatus.FAILED for p in products):
                reasons.append("A selected product failed verification.")
                blocked = True
            elif any(p.verification_status not in VERIFIED_PRODUCTS for p in products):
                reasons.append("The selected product is not verified.")
        failed = [r for r in project.relationships if r.source_id == role.id and r.strength.value == "Hard" and r.validation_status == RelationshipValidationStatus.FAILED]
        if failed:
            reasons.append("A hard dependency relationship has failed validation.")
            blocked = True
        incompatible = [r for r in project.relationships if r.relationship_type == RelationshipType.INCOMPATIBLE_WITH and r.source_id in selected_product_ids and r.target_id in selected_product_ids]
        if incompatible and products:
            reasons.append("Selected products are marked incompatible.")
            blocked = True
        if blocked:
            status = ReadinessStatus.BLOCKED
        elif not required and not products:
            status = ReadinessStatus.NOT_EVALUATED
            reasons.append("Optional role has no selected product.")
        elif role.current_status in COMPLETE_STATUSES and products and all(p.verification_status in VERIFIED_PRODUCTS for p in products):
            status = ReadinessStatus.READY
        elif products:
            status = ReadinessStatus.AT_RISK
            if role.integration_risk >= 4:
                reasons.append("Integration risk is high.")
            if role.required_by and role.required_by <= date.today() + timedelta(days=30) and role.current_status not in {RoleStatus.ORDERED, RoleStatus.RECEIVED, RoleStatus.INSPECTED, *COMPLETE_STATUSES}:
                reasons.append("Required soon but not ordered or received.")
        else:
            status = ReadinessStatus.INCOMPLETE
        result[role.id] = EntityReadiness(
            entity_id=role.id, name=role.role_name, status=status, reasons=reasons,
            unresolved_requirements=len(reasons), main_blocker=reasons[0] if status == ReadinessStatus.BLOCKED and reasons else None,
        )
    # Resolve hard role-to-role dependencies after baseline states exist.
    role_ids = set(result)
    hard_types = {RelationshipType.REQUIRES, RelationshipType.REQUIRES_COMPATIBLE, RelationshipType.POWERED_BY}
    for rel in project.relationships:
        if rel.source_id in role_ids and rel.target_id in role_ids and rel.strength.value == "Hard" and rel.relationship_type in hard_types:
            target = result[rel.target_id]
            if target.status in {ReadinessStatus.BLOCKED, ReadinessStatus.INCOMPLETE, ReadinessStatus.NOT_EVALUATED}:
                source = result[rel.source_id]
                message = f"Requires {target.name}, which is {target.status.value.lower()}."
                source.reasons.append(message)
                source.unresolved_requirements += 1
                source.status = ReadinessStatus.BLOCKED
                source.main_blocker = source.main_blocker or message
    return result


def evaluate_project_readiness(project: Project) -> ReadinessReport:
    roles = _role_readiness(project)
    names = project.entity_names()
    groups: dict[str, EntityReadiness] = {}
    for group in project.requirement_groups:
        if group.condition and group.condition_active is False:
            groups[group.id] = EntityReadiness(entity_id=group.id, name=group.group_name, status=ReadinessStatus.NOT_EVALUATED, reasons=["Conditional group is disabled."])
            continue
        member_states = [roles.get(member) for member in group.member_component_role_ids]
        ready = sum(state is not None and state.status in {ReadinessStatus.READY, ReadinessStatus.COMPLETED} for state in member_states)
        needed = len(member_states) if group.logic_type == LogicType.ALL_OF else (1 if group.logic_type == LogicType.ANY_OF else group.minimum_required_count or 0)
        if not member_states or needed <= 0 or needed > len(member_states):
            status, reason = ReadinessStatus.BLOCKED, "Requirement group cannot be satisfied with its current members."
        elif ready >= needed:
            status, reason = ReadinessStatus.READY, f"{ready} of {needed} required member(s) are ready."
        elif group.condition and group.condition_active is None:
            status, reason = ReadinessStatus.AT_RISK, "Conditional group has not been activated or disabled."
        elif group.requirement_strength == RequirementStrength.HARD:
            status, reason = ReadinessStatus.BLOCKED, f"Only {ready} of {needed} required member(s) are ready."
        else:
            status, reason = ReadinessStatus.AT_RISK, f"Only {ready} of {needed} recommended member(s) are ready."
        groups[group.id] = EntityReadiness(entity_id=group.id, name=group.group_name, status=status, reasons=[reason], satisfied_requirements=ready, unresolved_requirements=max(0, needed-ready), main_blocker=reason if status == ReadinessStatus.BLOCKED else None)

    capabilities: dict[str, EntityReadiness] = {}
    for cap in project.capabilities:
        relevant_roles = [state for role_id, state in roles.items() if next((r.capability_id for r in project.component_roles if r.id == role_id), None) == cap.id]
        relevant_groups = [groups[g.id] for g in project.requirement_groups if g.owner_id == cap.id]
        states = relevant_roles + relevant_groups
        if cap.requiredness == Requiredness.CONDITIONAL and not cap.condition_description:
            status, reasons = ReadinessStatus.AT_RISK, ["Conditional capability has no evaluable condition."]
        elif any(s.status == ReadinessStatus.BLOCKED for s in states):
            status, reasons = ReadinessStatus.BLOCKED, [next(s.main_blocker or s.reasons[0] for s in states if s.status == ReadinessStatus.BLOCKED)]
        elif states and all(s.status in {ReadinessStatus.READY, ReadinessStatus.COMPLETED, ReadinessStatus.NOT_EVALUATED} for s in states):
            status, reasons = ReadinessStatus.READY, ["All active requirements are ready."]
        elif states:
            status, reasons = ReadinessStatus.AT_RISK, ["Some capability requirements remain incomplete or unverified."]
        else:
            status, reasons = ReadinessStatus.NOT_EVALUATED, ["No component roles or groups define readiness."]
        capabilities[cap.id] = EntityReadiness(entity_id=cap.id, name=cap.name, status=status, reasons=reasons)

    milestones: dict[str, EntityReadiness] = {}
    sorted_milestones = sorted(project.milestones, key=lambda m: m.sequence_number)
    for milestone in sorted_milestones:
        cap_states = [capabilities[c.id] for c in project.capabilities if c.first_relevant_milestone_id == milestone.id]
        group_states = [groups[g.id] for g in project.requirement_groups if g.relevant_milestone_id == milestone.id and g.requirement_strength == RequirementStrength.HARD]
        role_states = [roles[r.id] for r in project.component_roles if r.first_required_milestone_id == milestone.id and r.requiredness == RoleRequiredness.MANDATORY]
        states = cap_states + group_states + role_states
        blocked_states = [s for s in states if s.status == ReadinessStatus.BLOCKED]
        if milestone.completed or project.current_stage.value == "Completed":
            status, reason = ReadinessStatus.COMPLETED, "Milestone completion is confirmed."
        elif blocked_states:
            status, reason = ReadinessStatus.BLOCKED, blocked_states[0].main_blocker or blocked_states[0].reasons[0]
        elif states and all(s.status in {ReadinessStatus.READY, ReadinessStatus.COMPLETED, ReadinessStatus.NOT_EVALUATED} for s in states):
            status, reason = ReadinessStatus.READY, "All mandatory milestone requirements are ready."
        elif states:
            status, reason = ReadinessStatus.AT_RISK, "Milestone has incomplete or unverified requirements."
        else:
            status, reason = ReadinessStatus.NOT_EVALUATED, "No readiness requirements are linked to this milestone."
        milestones[milestone.id] = EntityReadiness(entity_id=milestone.id, name=milestone.name, status=status, reasons=[reason], satisfied_requirements=sum(s.status in {ReadinessStatus.READY, ReadinessStatus.COMPLETED} for s in states), unresolved_requirements=sum(s.status not in {ReadinessStatus.READY, ReadinessStatus.COMPLETED, ReadinessStatus.NOT_EVALUATED} for s in states), main_blocker=reason if status == ReadinessStatus.BLOCKED else None)

    current = next((m for m in sorted_milestones if milestones[m.id].status not in {ReadinessStatus.READY, ReadinessStatus.COMPLETED}), sorted_milestones[-1] if sorted_milestones else None)
    current_state = milestones.get(current.id) if current else None
    blockers = [*filter(lambda x: x.status == ReadinessStatus.BLOCKED, roles.values()), *filter(lambda x: x.status == ReadinessStatus.BLOCKED, groups.values())]
    status = current_state.status if current_state else ReadinessStatus.NOT_EVALUATED
    reasons = list(current_state.reasons) if current_state else ["No milestones exist."]
    return ReadinessReport(status=status, reasons=reasons, current_milestone_id=current.id if current else None, component_roles=roles, requirement_groups=groups, capabilities=capabilities, milestones=milestones, blockers=blockers)


def evaluate_readiness(project: Project) -> list[ReadinessResult]:
    report = evaluate_project_readiness(project)
    return [ReadinessResult(item.entity_id, item.name, item.status, item.reasons[0] if item.reasons else "") for item in [*report.requirement_groups.values(), *report.capabilities.values()]]
