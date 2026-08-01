from dataclasses import dataclass

from models.enums import ReadinessStatus
from models.project import Project
from models.readiness import ReadinessReport
from services.graph_analysis import dependency_centrality


@dataclass(frozen=True)
class RecommendedAction:
    role_id: str
    text: str
    score: tuple


def recommended_actions(project: Project, report: ReadinessReport) -> list[RecommendedAction]:
    centrality = dependency_centrality(project)
    current = report.current_milestone_id
    ratings = {(r.component_role_id, r.milestone_id): r.rating for r in project.role_milestone_ratings}
    actions = []
    for role in project.component_roles:
        state = report.component_roles.get(role.id)
        if not state or state.status in {ReadinessStatus.READY, ReadinessStatus.COMPLETED, ReadinessStatus.NOT_EVALUATED}:
            continue
        if state.main_blocker and "No selected product" in state.main_blocker:
            text = f"Select a product for {role.role_name}"
        elif "not verified" in " ".join(state.reasons).lower():
            text = f"Verify the selected product for {role.role_name}"
        elif role.current_status.value == "Received":
            text = f"Mark {role.role_name} as inspected"
        else:
            text = f"Resolve {role.role_name}: {state.reasons[0] if state.reasons else 'complete its requirements'}"
        score = (role.first_required_milestone_id == current, ratings.get((role.id, current), 0), state.status == ReadinessStatus.BLOCKED, -(role.required_by.toordinal() if role.required_by else 9999999), centrality.get(role.id, 0))
        actions.append(RecommendedAction(role.id, text, score))
    return sorted(actions, key=lambda item: item.score, reverse=True)
