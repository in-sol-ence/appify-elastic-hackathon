from datetime import date, timedelta

from models.enums import (
    EntityType, LogicType, RelationshipType, RequirementStrength, Requiredness,
    RoleRequiredness, RoleStatus, Strength,
)
from models.project import (
    Capability, ComponentRole, Milestone, Project, Relationship,
    RequirementGroup, RoleMilestoneRating,
)


def build_rover_template() -> Project:
    today = date.today()
    milestone_specs = [
        ("Compute setup", 1, 21),
        ("Manual mobility", 2, 45),
        ("Localization", 3, 75),
        ("Autonomous navigation", 4, 105),
        ("Final demonstration", 5, 120),
    ]
    milestones = [
        Milestone(
            name=name,
            description=f"Complete and validate {name.lower()}.",
            sequence_number=sequence,
            target_date=today + timedelta(days=days),
            mandatory=True,
            completion_criteria=f"{name} acceptance test passes.",
        )
        for name, sequence, days in milestone_specs
    ]
    milestone_by_name = {item.name: item for item in milestones}

    capability_specs = [
        ("Compute", "Run onboard robotics software", Requiredness.MANDATORY, "Compute setup"),
        ("Supply power", "Provide stable electrical power", Requiredness.MANDATORY, "Compute setup"),
        ("Move", "Drive the rover under manual control", Requiredness.MANDATORY, "Manual mobility"),
        ("Communicate", "Exchange commands and telemetry", Requiredness.MANDATORY, "Manual mobility"),
        ("Localize", "Estimate rover position", Requiredness.MANDATORY, "Localization"),
        ("Detect obstacles", "Detect nearby obstacles", Requiredness.CONDITIONAL, "Autonomous navigation"),
        ("Navigate autonomously", "Plan and execute autonomous motion", Requiredness.DEFERRED, "Autonomous navigation"),
        ("Record data", "Record sensor and system data", Requiredness.OPTIONAL, "Compute setup"),
    ]
    capabilities = [
        Capability(
            name=name,
            description=description,
            requiredness=requiredness,
            first_relevant_milestone_id=milestone_by_name[milestone].id,
            acceptance_criteria=f"Demonstrate that the rover can {name.lower()}.",
            condition_description=("Required when autonomous obstacle avoidance is selected." if requiredness == Requiredness.CONDITIONAL else None),
        )
        for name, description, requiredness, milestone in capability_specs
    ]
    capability_by_name = {item.name: item for item in capabilities}

    role_specs = [
        ("Onboard computer", "Compute", "Runs ROS2 and control software", "Compute", "Compute setup", RoleRequiredness.MANDATORY),
        ("Storage", "Compute", "Stores the operating system, software, and logs", "Compute", "Compute setup", RoleRequiredness.MANDATORY),
        ("Computer power converter", "Power", "Supplies regulated compute power", "Supply power", "Compute setup", RoleRequiredness.MANDATORY),
        ("Drive motors", "Mobility", "Generate wheel torque", "Move", "Manual mobility", RoleRequiredness.MANDATORY),
        ("Motor driver", "Mobility", "Controls motor current from the computer", "Move", "Manual mobility", RoleRequiredness.MANDATORY),
        ("Battery", "Power", "Supplies mobile power", "Supply power", "Manual mobility", RoleRequiredness.MANDATORY),
        ("Wheels", "Mobility", "Transfer motor torque to the ground", "Move", "Manual mobility", RoleRequiredness.MANDATORY),
        ("Localization system", "Sensing", "Estimates rover position", "Localize", "Localization", RoleRequiredness.MANDATORY),
        ("Obstacle-detection system", "Sensing", "Detects obstacles for navigation", "Detect obstacles", "Autonomous navigation", RoleRequiredness.CONDITIONAL),
    ]
    roles = [
        ComponentRole(
            role_name=name,
            category=category,
            purpose=purpose,
            capability_id=capability_by_name[capability].id,
            required_quantity=(2 if name == "Drive motors" else 1),
            requiredness=requiredness,
            first_required_milestone_id=milestone_by_name[milestone].id,
            required_by=milestone_by_name[milestone].target_date,
            necessity_confidence=(75 if requiredness == RoleRequiredness.CONDITIONAL else 95),
            replacement_difficulty=3,
            integration_risk=(4 if name in {"Motor driver", "Localization system", "Obstacle-detection system"} else 3),
            functional_acceptance_criteria=f"{name} passes its functional test.",
            current_status=RoleStatus.PROPOSED,
            condition_description=("Required for autonomous obstacle-aware navigation." if requiredness == RoleRequiredness.CONDITIONAL else None),
        )
        for name, category, purpose, capability, milestone, requiredness in role_specs
    ]
    role_by_name = {item.role_name: item for item in roles}

    rating_values = {
        "Onboard computer": [5, 5, 5, 5, 5],
        "Storage": [4, 3, 3, 4, 3],
        "Computer power converter": [5, 5, 5, 5, 5],
        "Drive motors": [0, 5, 2, 4, 5],
        "Motor driver": [0, 5, 2, 5, 5],
        "Battery": [2, 5, 4, 5, 5],
        "Wheels": [0, 5, 1, 4, 5],
        "Localization system": [0, 1, 5, 5, 5],
        "Obstacle-detection system": [0, 1, 2, 5, 5],
    }
    ratings = [
        RoleMilestoneRating(component_role_id=role.id, milestone_id=milestone.id, rating=rating_values[role.role_name][index])
        for role in roles for index, milestone in enumerate(milestones)
    ]

    def rel(source: str, relation: RelationshipType, target: str, source_type: EntityType, target_type: EntityType, milestone: str) -> Relationship:
        source_id = role_by_name[source].id if source_type == EntityType.COMPONENT_ROLE else capability_by_name[source].id
        if target_type == EntityType.COMPONENT_ROLE:
            target_id = role_by_name[target].id
        elif target_type == EntityType.CAPABILITY:
            target_id = capability_by_name[target].id
        else:
            target_id = milestone_by_name[target].id
        return Relationship(
            source_id=source_id,
            source_type=source_type,
            relationship_type=relation,
            target_id=target_id,
            target_type=target_type,
            strength=Strength.HARD,
            relevant_milestone_id=milestone_by_name[milestone].id,
        )

    relationships = [
        rel("Onboard computer", RelationshipType.ENABLES, "Compute", EntityType.COMPONENT_ROLE, EntityType.CAPABILITY, "Compute setup"),
        rel("Onboard computer", RelationshipType.REQUIRED_FOR, "Compute setup", EntityType.COMPONENT_ROLE, EntityType.MILESTONE, "Compute setup"),
        rel("Drive motors", RelationshipType.REQUIRES_COMPATIBLE, "Motor driver", EntityType.COMPONENT_ROLE, EntityType.COMPONENT_ROLE, "Manual mobility"),
        rel("Drive motors", RelationshipType.POWERED_BY, "Battery", EntityType.COMPONENT_ROLE, EntityType.COMPONENT_ROLE, "Manual mobility"),
        rel("Motor driver", RelationshipType.CONNECTS_TO, "Onboard computer", EntityType.COMPONENT_ROLE, EntityType.COMPONENT_ROLE, "Manual mobility"),
        rel("Localization system", RelationshipType.ENABLES, "Localize", EntityType.COMPONENT_ROLE, EntityType.CAPABILITY, "Localization"),
        rel("Obstacle-detection system", RelationshipType.ENABLES, "Detect obstacles", EntityType.COMPONENT_ROLE, EntityType.CAPABILITY, "Autonomous navigation"),
    ]

    groups = [
        RequirementGroup(
            group_name="Compute subsystem",
            owner_id=capability_by_name["Compute"].id,
            owner_type=EntityType.CAPABILITY,
            logic_type=LogicType.ALL_OF,
            member_component_role_ids=[role_by_name[name].id for name in ["Onboard computer", "Storage", "Computer power converter"]],
            requirement_strength=RequirementStrength.HARD,
            relevant_milestone_id=milestone_by_name["Compute setup"].id,
        ),
        RequirementGroup(
            group_name="Manual mobility subsystem",
            owner_id=capability_by_name["Move"].id,
            owner_type=EntityType.CAPABILITY,
            logic_type=LogicType.ALL_OF,
            member_component_role_ids=[role_by_name[name].id for name in ["Drive motors", "Motor driver", "Battery", "Wheels", "Onboard computer"]],
            requirement_strength=RequirementStrength.HARD,
            relevant_milestone_id=milestone_by_name["Manual mobility"].id,
        ),
        RequirementGroup(
            group_name="Localization subsystem",
            owner_id=capability_by_name["Localize"].id,
            owner_type=EntityType.CAPABILITY,
            logic_type=LogicType.ANY_OF,
            member_component_role_ids=[role_by_name["Localization system"].id],
            requirement_strength=RequirementStrength.HARD,
            relevant_milestone_id=milestone_by_name["Localization"].id,
        ),
        RequirementGroup(
            group_name="Obstacle detection",
            owner_id=capability_by_name["Detect obstacles"].id,
            owner_type=EntityType.CAPABILITY,
            logic_type=LogicType.ANY_OF,
            member_component_role_ids=[role_by_name["Obstacle-detection system"].id],
            requirement_strength=RequirementStrength.SOFT,
            relevant_milestone_id=milestone_by_name["Autonomous navigation"].id,
            condition="Required for obstacle-aware autonomous navigation.",
        ),
    ]

    return Project(
        final_deadline=today + timedelta(days=120),
        milestones=milestones,
        capabilities=capabilities,
        component_roles=roles,
        role_milestone_ratings=ratings,
        relationships=relationships,
        requirement_groups=groups,
    )


def build_sample_project() -> Project:
    project = build_rover_template()
    project.name = "Autonomous Target Rover"
    project.short_description = "A compact rover that drives to targets and demonstrates autonomous navigation."
    project.total_budget = 1500
    project.software_platform = "Ubuntu 22.04 and ROS2 Humble"
    project.location = "Hackathon laboratory"
    project.team_size = 4
    return project
