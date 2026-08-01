from services.search_profile import build_component_search_profile
from services.templates import build_sample_project


def test_motor_driver_profile_has_structured_requirements_and_connections():
    project=build_sample_project();role=next(r for r in project.component_roles if r.role_name=="Motor driver")
    role.acceptance_requirements={"voltage":"24 V","current":"15 A","interface":"PWM or UART"};role.functional_acceptance_criteria="Peak current 30 A and channel count 2"
    profile=build_component_search_profile(project,role.id)
    assert profile.category=="motor_driver"
    assert any(r.field=="required_voltage_v" for r in profile.hard_requirements)
    assert any(r.field=="control_interfaces" for r in profile.hard_requirements)
    assert profile.connected_components
    assert profile.preferred_requirements


def test_computer_and_lidar_profiles_handle_missing_optional_fields():
    project=build_sample_project()
    computer=build_component_search_profile(project,next(r.id for r in project.component_roles if r.role_name=="Onboard computer"))
    lidar=build_component_search_profile(project,next(r.id for r in project.component_roles if "Obstacle" in r.role_name))
    assert computer.category=="onboard_computer"
    assert lidar.category=="lidar"
    assert computer.natural_language_description
