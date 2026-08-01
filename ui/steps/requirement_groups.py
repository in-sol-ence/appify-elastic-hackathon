import streamlit as st

from models.enums import EntityType, LogicType, RequirementStrength
from models.project import RequirementGroup
from ui.shared import enum_values, get_wizard, set_step_errors


def render() -> None:
    project = get_wizard().current_project
    st.subheader("Requirement groups")
    st.write("Represent subsystem rules involving several interchangeable or jointly required roles.")
    with st.expander("How requirement groups work"):
        st.write("ALL_OF requires every member, ANY_OF requires one member, and N_OF_M requires a chosen minimum. Groups can be hard blockers or soft recommendations.")
    owners = {item.id: (EntityType.CAPABILITY, item.name) for item in project.capabilities}
    owners.update({item.id: (EntityType.MILESTONE, item.name) for item in project.milestones})
    roles = {item.id: item.role_name for item in project.component_roles}
    milestones = {item.id: item.name for item in project.milestones}
    if not owners or not roles:
        st.warning("Add at least one capability or milestone and one component role first.")
        set_step_errors([])
        return
    owner_label = lambda item: f"{owners[item][1]} ({owners[item][0].value})"
    milestone_options = [None, *milestones]
    milestone_label = lambda item: "— Any milestone —" if item is None else milestones[item]

    st.markdown("#### Add requirement group")
    with st.form("group_add_form", clear_on_submit=True):
        name = st.text_input("Group name")
        owner = st.selectbox("Owner capability or milestone", list(owners), format_func=owner_label)
        logic = st.selectbox("Logic type", enum_values(LogicType))
        members = st.multiselect("Member component roles", list(roles), format_func=lambda item: roles[item])
        strength = st.selectbox("Requirement strength", enum_values(RequirementStrength))
        relevant = st.selectbox("Relevant milestone", milestone_options, format_func=milestone_label)
        condition = st.text_input("Optional condition")
        minimum = st.number_input("Minimum required count (N_OF_M only)", min_value=1, value=1, step=1)
        if st.form_submit_button("Add group"):
            try:
                project.requirement_groups.append(RequirementGroup(
                    group_name=name.strip(), owner_id=owner, owner_type=owners[owner][0],
                    logic_type=LogicType(logic), member_component_role_ids=members,
                    requirement_strength=RequirementStrength(strength), relevant_milestone_id=relevant,
                    condition=condition, minimum_required_count=(int(minimum) if logic == LogicType.N_OF_M.value else None),
                ))
                st.rerun()
            except Exception as error:
                st.error(str(error))

    st.markdown("#### Existing groups")
    for group in list(project.requirement_groups):
        with st.expander(f"{group.group_name} · {group.logic_type.value}"):
            name = st.text_input("Group name", value=group.group_name, key=f"group_name_{group.id}")
            owner_options = list(owners)
            owner_index = owner_options.index(group.owner_id) if group.owner_id in owner_options else 0
            owner = st.selectbox("Owner", owner_options, index=owner_index, format_func=owner_label, key=f"group_owner_{group.id}")
            logic_values = enum_values(LogicType)
            logic = st.selectbox("Logic", logic_values, index=logic_values.index(group.logic_type.value), key=f"group_logic_{group.id}")
            valid_members = [item for item in group.member_component_role_ids if item in roles]
            members = st.multiselect("Members", list(roles), default=valid_members, format_func=lambda item: roles[item], key=f"group_members_{group.id}")
            strength_values = enum_values(RequirementStrength)
            strength = st.selectbox("Strength", strength_values, index=strength_values.index(group.requirement_strength.value), key=f"group_strength_{group.id}")
            milestone_index = milestone_options.index(group.relevant_milestone_id) if group.relevant_milestone_id in milestone_options else 0
            relevant = st.selectbox("Relevant milestone", milestone_options, index=milestone_index, format_func=milestone_label, key=f"group_milestone_{group.id}")
            condition = st.text_input("Condition", value=group.condition, key=f"group_condition_{group.id}")
            minimum = st.number_input("Minimum required", min_value=1, value=group.minimum_required_count or 1, step=1, key=f"group_min_{group.id}")
            save, remove = st.columns(2)
            if save.button("Update", key=f"group_save_{group.id}"):
                try:
                    replacement = RequirementGroup(
                        id=group.id, group_name=name.strip(), owner_id=owner, owner_type=owners[owner][0],
                        logic_type=LogicType(logic), member_component_role_ids=members,
                        requirement_strength=RequirementStrength(strength), relevant_milestone_id=relevant,
                        condition=condition, minimum_required_count=(int(minimum) if logic == LogicType.N_OF_M.value else None),
                    )
                    project.requirement_groups[project.requirement_groups.index(group)] = replacement
                    st.rerun()
                except Exception as error:
                    st.error(str(error))
            if remove.button("Remove", key=f"group_remove_{group.id}"):
                project.requirement_groups.remove(group); st.rerun()
    set_step_errors([])
