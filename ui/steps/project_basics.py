from datetime import date, timedelta

import streamlit as st

from models.enums import OperatingEnvironment, ProjectStage, RiskTolerance
from ui.shared import enum_values, get_wizard, set_step_errors


def render() -> None:
    wizard = get_wizard()
    project = wizard.current_project
    st.subheader("Project basics")
    notice = wizard.editing_state.pop("notice", None)
    if notice:
        st.success(notice)
    st.write("Define the project boundary, schedule, operating context, and risk posture.")

    project.name = st.text_input("Project name *", value=project.name, key="basics_name")
    project.short_description = st.text_area("Short description *", value=project.short_description, key="basics_description")
    first, second = st.columns(2)
    with first:
        project.total_budget = st.number_input("Total budget ($)", min_value=0.0, value=float(project.total_budget), step=100.0, key="basics_budget")
        deadline = project.final_deadline or date.today() + timedelta(days=90)
        project.final_deadline = st.date_input("Final deadline *", value=deadline, key="basics_deadline")
        stage_values = enum_values(ProjectStage)
        project.current_stage = ProjectStage(st.selectbox("Current project stage", stage_values, index=stage_values.index(project.current_stage.value), key="basics_stage"))
        environment_values = enum_values(OperatingEnvironment)
        project.operating_environment = OperatingEnvironment(st.selectbox("Operating environment", environment_values, index=environment_values.index(project.operating_environment.value), key="basics_environment"))
    with second:
        project.location = st.text_input("Location", value=project.location, key="basics_location")
        project.software_platform = st.text_input("Software platform", value=project.software_platform, placeholder="Ubuntu 22.04, ROS2 Humble", key="basics_platform")
        project.team_size = st.number_input("Team size", min_value=1, value=int(project.team_size), step=1, key="basics_team")
        risk_values = enum_values(RiskTolerance)
        project.risk_tolerance = RiskTolerance(st.selectbox("Risk tolerance", risk_values, index=risk_values.index(project.risk_tolerance.value), key="basics_risk"))
    set_step_errors([])
