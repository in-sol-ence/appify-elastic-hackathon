from services.graph_analysis import component_impact, dependency_centrality
from services.templates import build_sample_project


def test_centrality_and_impact_are_derived_from_graph() -> None:
    project=build_sample_project(); role=next(r for r in project.component_roles if r.role_name=="Onboard computer")
    centrality=dependency_centrality(project); impact=component_impact(project,role.id)
    assert 0 <= centrality[role.id] <= 1
    assert "Compute setup" in impact["milestones"]
    assert "Compute" in impact["capabilities"]
