import streamlit as st

from models.enums import (
    EntityType, RelationshipType, RelationshipValidationStatus, Strength,
)
from models.project import Relationship
from services.validation import validate_project
from ui.shared import enum_values, get_wizard, set_step_errors


ALLOWED = {
    (EntityType.CAPABILITY, EntityType.COMPONENT_ROLE),
    (EntityType.COMPONENT_ROLE, EntityType.CAPABILITY),
    (EntityType.COMPONENT_ROLE, EntityType.COMPONENT_ROLE),
    (EntityType.COMPONENT_ROLE, EntityType.MILESTONE),
    (EntityType.PRODUCT, EntityType.PRODUCT),
}


def _entities(project):
    result = {}
    for item in project.capabilities:
        result[item.id] = (EntityType.CAPABILITY, item.name)
    for item in project.component_roles:
        result[item.id] = (EntityType.COMPONENT_ROLE, item.role_name)
    for item in project.milestones:
        result[item.id] = (EntityType.MILESTONE, item.name)
    for item in project.products:
        result[item.id] = (EntityType.PRODUCT, item.product_name)
    return result


def _targets(source_id, entities):
    source_type = entities[source_id][0]
    return [item_id for item_id, (item_type, _) in entities.items() if item_id != source_id and (source_type, item_type) in ALLOWED]


def render() -> None:
    project = get_wizard().current_project
    st.subheader("Direct dependencies")
    st.write("Build readable dependency sentences. The graph itself remains read-only.")
    entities = _entities(project)
    labels = {item_id: f"{name} ({item_type.value})" for item_id, (item_type, name) in entities.items()}
    milestones = {item.id: item.name for item in project.milestones}
    milestone_options = [None, *milestones]
    format_milestone = lambda item: "— Any milestone —" if item is None else milestones.get(item, "Deleted milestone")

    if not entities:
        st.warning("Add capabilities, component roles, or products before defining dependencies.")
        set_step_errors([])
        return

    st.markdown("#### Add relationship")
    source_options = [item_id for item_id in entities if _targets(item_id, entities)]
    if source_options:
        source = st.selectbox("Source entity", source_options, format_func=lambda item: labels[item], key="dep_add_source")
        relation = st.selectbox("Relationship", enum_values(RelationshipType), key="dep_add_type")
        targets = _targets(source, entities)
        target = st.selectbox("Target entity", targets, format_func=lambda item: labels[item], key="dep_add_target")
        left, right = st.columns(2)
        strength = left.selectbox("Strength", enum_values(Strength), key="dep_add_strength")
        relevant = right.selectbox("Relevant milestone", milestone_options, format_func=format_milestone, key="dep_add_milestone")
        condition = st.text_input("Optional condition", key="dep_add_condition")
        notes = st.text_area("Notes", key="dep_add_notes")
        status = st.selectbox("Validation status", enum_values(RelationshipValidationStatus), key="dep_add_validation")
        st.caption(f"Sentence: **{labels[source]} {relation.lower()} {labels[target]}**")
        if st.button("Add relationship", key="dep_add_button"):
            project.relationships.append(Relationship(
                source_id=source, source_type=entities[source][0], relationship_type=RelationshipType(relation),
                target_id=target, target_type=entities[target][0], strength=Strength(strength),
                relevant_milestone_id=relevant, condition=condition, notes=notes,
                validation_status=RelationshipValidationStatus(status),
            ))
            st.rerun()

    st.markdown("#### Existing relationships")
    for relationship in list(project.relationships):
        title = f"{labels.get(relationship.source_id, 'Deleted')} {relationship.relationship_type.value.lower()} {labels.get(relationship.target_id, 'Deleted')}"
        with st.expander(title):
            if relationship.source_id not in entities:
                st.error("The source entity was deleted. Remove or replace this relationship.")
                if st.button("Remove relationship", key=f"dep_remove_{relationship.id}"):
                    project.relationships.remove(relationship); st.rerun()
                continue
            source = st.selectbox("Source", list(entities), index=list(entities).index(relationship.source_id), format_func=lambda item: labels[item], key=f"dep_source_{relationship.id}")
            targets = _targets(source, entities)
            target_index = targets.index(relationship.target_id) if relationship.target_id in targets else 0
            if not targets:
                st.error("No valid target exists for this source type.")
                continue
            target = st.selectbox("Target", targets, index=target_index, format_func=lambda item: labels[item], key=f"dep_target_{relationship.id}")
            relation_values = enum_values(RelationshipType)
            relation = st.selectbox("Relationship", relation_values, index=relation_values.index(relationship.relationship_type.value), key=f"dep_type_{relationship.id}")
            strength_values = enum_values(Strength)
            strength = st.selectbox("Strength", strength_values, index=strength_values.index(relationship.strength.value), key=f"dep_strength_{relationship.id}")
            milestone_index = milestone_options.index(relationship.relevant_milestone_id) if relationship.relevant_milestone_id in milestone_options else 0
            relevant = st.selectbox("Relevant milestone", milestone_options, index=milestone_index, format_func=format_milestone, key=f"dep_milestone_{relationship.id}")
            condition = st.text_input("Condition", value=relationship.condition, key=f"dep_condition_{relationship.id}")
            notes = st.text_area("Notes", value=relationship.notes, key=f"dep_notes_{relationship.id}")
            validation_values = enum_values(RelationshipValidationStatus)
            status = st.selectbox("Validation status", validation_values, index=validation_values.index(relationship.validation_status.value), key=f"dep_validation_{relationship.id}")
            save, remove = st.columns(2)
            if save.button("Update", key=f"dep_save_{relationship.id}"):
                replacement = Relationship(
                    id=relationship.id, source_id=source, source_type=entities[source][0],
                    relationship_type=RelationshipType(relation), target_id=target, target_type=entities[target][0],
                    strength=Strength(strength), relevant_milestone_id=relevant, condition=condition,
                    notes=notes, validation_status=RelationshipValidationStatus(status),
                )
                project.relationships[project.relationships.index(relationship)] = replacement
                st.rerun()
            if remove.button("Remove", key=f"dep_remove_{relationship.id}"):
                project.relationships.remove(relationship); st.rerun()

    cycles = [item for item in validate_project(project) if item.code == "circular_dependency"]
    for item in cycles:
        st.warning(item.message)
    set_step_errors([])
