from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import streamlit as st

from models.enums import FindingSeverity
from models.project import Project, ValidationFinding


@dataclass
class WizardState:
    project_id: str | None = None
    project: Project = field(default_factory=Project)
    selected_project_id: str | None = None
    selected_project: Project | None = None
    current_page: str = "home"
    current_project_tab: str = "Overview"
    selected_component_id: str | None = None
    editing_mode: bool = False
    readiness_result: Any = None
    current_step: int = 1
    validation_findings: list[ValidationFinding] = field(default_factory=list)
    last_saved_at: datetime | None = None
    persistence_status: str = "unsaved"
    selected_template: str = "Autonomous rover template"
    editing_state: dict[str, Any] = field(default_factory=dict)

    @property
    def current_project(self) -> Project:
        """Compatibility name used by existing step renderers."""
        return self.project

    @current_project.setter
    def current_project(self, value: Project) -> None:
        self.project = value

    @property
    def last_saved_timestamp(self) -> datetime | None:
        return self.last_saved_at

    @last_saved_timestamp.setter
    def last_saved_timestamp(self, value: datetime | None) -> None:
        self.last_saved_at = value


STEPS = [
    "Starting point", "Project basics", "Milestones", "Capabilities",
    "Component roles", "Criticality ratings", "Dependencies",
    "Requirement groups", "Product selections", "Review and validation",
]


def get_wizard() -> WizardState:
    if "wizard_state" not in st.session_state:
        st.session_state.wizard_state = WizardState()
    return st.session_state.wizard_state


def reset_wizard() -> None:
    for key in list(st.session_state):
        del st.session_state[key]
    st.session_state.wizard_state = WizardState()


def set_step_errors(errors: list[ValidationFinding]) -> None:
    get_wizard().editing_state["step_errors"] = errors


def step_errors() -> list[ValidationFinding]:
    return get_wizard().editing_state.get("step_errors", [])


def blocking_ui_error(code: str, message: str) -> ValidationFinding:
    return ValidationFinding(severity=FindingSeverity.BLOCKING, code=code, message=message)


def show_findings(findings: list[ValidationFinding]) -> None:
    for item in findings:
        if item.severity == FindingSeverity.BLOCKING:
            st.error(item.message)
        elif item.severity == FindingSeverity.WARNING:
            st.warning(item.message)
        else:
            st.info(item.message)


def project_summary(project: Project) -> None:
    with st.expander("Project summary", expanded=False):
        left, right = st.columns(2)
        with left:
            st.write(f"**Name:** {project.name or 'Untitled project'}")
            st.write(f"**Stage:** {project.current_stage.value}")
            st.write(f"**Budget:** ${project.total_budget:,.2f}")
        with right:
            st.write(f"**Milestones:** {len(project.milestones)}")
            st.write(f"**Capabilities:** {len(project.capabilities)}")
            st.write(f"**Component roles / products:** {len(project.component_roles)} / {len(project.products)}")


def step_indicator(current_step: int) -> None:
    labels = []
    for index, name in enumerate(STEPS, start=1):
        if index == current_step:
            labels.append(f"**{index}. {name}**")
        else:
            labels.append(f"{index}. {name}")
    st.markdown("  ·  ".join(labels))
    st.progress(current_step / len(STEPS))


def enum_values(enum_type: type) -> list[str]:
    return [item.value for item in enum_type]


def editor_records(value: Any) -> list[dict[str, Any]]:
    """Normalize st.data_editor output for list and DataFrame inputs."""
    if hasattr(value, "to_dict"):
        return value.to_dict("records")
    return list(value)
