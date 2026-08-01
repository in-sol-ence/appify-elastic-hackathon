import streamlit as st

from models.enums import (
    PurchaseStatus, RelationshipValidationStatus, RoleRequiredness, RoleStatus,
    SelectionStatus, VerificationStatus,
)
from models.project import ProductSelection
from repositories.project_repository import ProjectRepository
from services.graph_analysis import component_impact, dependency_centrality
from ui.persistence import save_wizard_project, show_repository_error
from ui.shared import enum_values, get_wizard


def _save(state, repository):
    save_wizard_project(state, repository, state.persistence_status if state.persistence_status in {"draft", "active", "archived"} else "active")
    state.readiness_result = None


def render(project, report, repository: ProjectRepository) -> None:
    state = get_wizard(); role = next((r for r in project.component_roles if r.id == state.selected_component_id), None)
    if not role:
        state.selected_component_id = None; return
    names = project.entity_names(); readiness = report.component_roles[role.id]
    with st.container(border=True):
        close, title = st.columns([1, 8])
        if close.button("Close", key="component_close"): state.selected_component_id=None; st.rerun()
        title.subheader(f"Component: {role.role_name}")
        title.write(f"{readiness.status.value} · {readiness.main_blocker or (readiness.reasons[0] if readiness.reasons else 'No blocker')}")
        tabs = st.tabs(["Role information", "Dependencies", "Products", "Status and impact"])
        with tabs[0]:
            with st.form(f"role_edit_{role.id}"):
                name=st.text_input("Role name",role.role_name); category=st.text_input("Category",role.category); purpose=st.text_area("Purpose",role.purpose)
                caps={c.id:c.name for c in project.capabilities}; cap=st.selectbox("Capability",[None,*caps],index=[None,*caps].index(role.capability_id) if role.capability_id in caps else 0,format_func=lambda x:"Not assigned" if x is None else caps[x])
                reqs=enum_values(RoleRequiredness); req=st.selectbox("Requiredness",reqs,index=reqs.index(role.requiredness.value)); condition=st.text_input("Condition",role.condition_description or "")
                qty=st.number_input("Required quantity",1,value=role.required_quantity); milestones={m.id:m.name for m in project.milestones}; mid=st.selectbox("First required milestone",[None,*milestones],index=[None,*milestones].index(role.first_required_milestone_id) if role.first_required_milestone_id in milestones else 0,format_func=lambda x:"Not assigned" if x is None else milestones[x])
                required_by=st.date_input("Required-by date",role.required_by); criteria=st.text_area("Functional acceptance criteria",role.functional_acceptance_criteria)
                st.markdown("**Structured acceptance requirements**")
                requirement_values={}
                for requirement_key, requirement_label in [("voltage","Voltage"),("current","Current"),("interface","Interface"),("dimensions","Dimensions"),("operating_system","Operating-system support"),("software","Software compatibility"),("mechanical","Mechanical requirements"),("other","Other requirements")]:
                    requirement_values[requirement_key]=st.text_input(requirement_label,role.acceptance_requirements.get(requirement_key,""),key=f"role_req_{role.id}_{requirement_key}")
                confidence=st.slider("Necessity confidence",0,100,role.necessity_confidence); replacement=st.slider("Replacement difficulty",1,5,role.replacement_difficulty); risk=st.slider("Integration risk",1,5,role.integration_risk)
                if st.form_submit_button("Save component role"):
                    role.role_name=name; role.category=category; role.purpose=purpose; role.capability_id=cap; role.requiredness=RoleRequiredness(req); role.condition_description=condition or None; role.required_quantity=int(qty); role.first_required_milestone_id=mid; role.required_by=required_by; role.functional_acceptance_criteria=criteria; role.acceptance_requirements={key:value for key,value in requirement_values.items() if value.strip()}; role.necessity_confidence=confidence; role.replacement_difficulty=replacement; role.integration_risk=risk
                    try: _save(state,repository); st.success("Component role saved."); st.rerun()
                    except Exception as error: show_repository_error(error,"saved")
            st.markdown("**Criticality by milestone**")
            ratings=[{"Milestone":names.get(r.milestone_id,"Deleted"),"Rating":r.rating} for r in project.role_milestone_ratings if r.component_role_id==role.id]
            st.dataframe(ratings,hide_index=True,use_container_width=True)
            st.write(f"Dependency centrality: {dependency_centrality(project).get(role.id,0):.2f}")
        with tabs[1]:
            rels=[r for r in project.relationships if r.source_id==role.id or r.target_id==role.id]
            if not rels: st.caption("No direct dependencies.")
            for rel in rels:
                direction="→" if rel.source_id==role.id else "←"
                other=rel.target_id if rel.source_id==role.id else rel.source_id
                st.write(f"{direction} **{rel.relationship_type.value}** {names.get(other,'Deleted')} · {rel.strength.value} · {rel.validation_status.value}")
                if rel.validation_status==RelationshipValidationStatus.UNVERIFIED and st.button("Mark verified",key=f"verify_rel_{rel.id}"):
                    rel.validation_status=RelationshipValidationStatus.USER_CONFIRMED
                    try: _save(state,repository); st.rerun()
                    except Exception as error: show_repository_error(error,"saved")
            st.markdown("**Requirement-group membership**")
            memberships=[g for g in project.requirement_groups if role.id in g.member_component_role_ids]
            for group in memberships: st.write(f"{group.group_name}: {group.logic_type.value} · {group.requirement_strength.value} · {report.requirement_groups[group.id].status.value}")
        with tabs[2]:
            products=[p for p in project.products if p.component_role_id==role.id]
            for product in list(products):
                with st.expander(f"{product.product_name} · {product.selection_status.value}{' · PRIMARY' if product.primary_product else ''}"):
                    with st.form(f"product_edit_{product.id}"):
                        manufacturer=st.text_input("Manufacturer",product.manufacturer); pname=st.text_input("Product name",product.product_name); model=st.text_input("Model",product.model); part=st.text_input("Part number",product.manufacturer_part_number)
                        qty=st.number_input("Quantity",1,value=product.quantity); price=st.number_input("Expected unit price",0.0,value=float(product.expected_unit_price)); supplier=st.text_input("Supplier name",product.supplier_name); supplier_url=st.text_input("Supplier URL",product.supplier_url); manufacturer_url=st.text_input("Manufacturer URL",product.manufacturer_url)
                        hw=st.text_input("Hardware revision",product.hardware_revision); fw=st.text_input("Firmware version",product.firmware_version)
                        selection=st.selectbox("Selection status",enum_values(SelectionStatus),index=enum_values(SelectionStatus).index(product.selection_status.value)); purchase=st.selectbox("Purchase status",enum_values(PurchaseStatus),index=enum_values(PurchaseStatus).index(product.purchase_status.value)); verification=st.selectbox("Verification status",enum_values(VerificationStatus),index=enum_values(VerificationStatus).index(product.verification_status.value)); primary=st.checkbox("Primary product",product.primary_product); alternatives=st.checkbox("Alternatives allowed",product.alternatives_allowed); notes=st.text_area("Notes",product.notes)
                        save,remove=st.columns(2)
                        if save.form_submit_button("Save product"):
                            if primary:
                                for other in products: other.primary_product=False
                            product.manufacturer=manufacturer; product.product_name=pname; product.model=model; product.manufacturer_part_number=part; product.quantity=int(qty); product.expected_unit_price=price; product.supplier_name=supplier; product.supplier_url=supplier_url; product.manufacturer_url=manufacturer_url; product.hardware_revision=hw; product.firmware_version=fw; product.selection_status=SelectionStatus(selection); product.purchase_status=PurchaseStatus(purchase); product.verification_status=VerificationStatus(verification); product.primary_product=primary; product.alternatives_allowed=alternatives; product.notes=notes
                            try: _save(state,repository); st.rerun()
                            except Exception as error: show_repository_error(error,"saved")
                        if remove.form_submit_button("Remove product"):
                            project.products.remove(product)
                            try: _save(state,repository); st.rerun()
                            except Exception as error: show_repository_error(error,"saved")
            with st.expander("Add product manually",expanded=not products):
                with st.form(f"product_add_{role.id}"):
                    manufacturer=st.text_input("Manufacturer"); pname=st.text_input("Product name *"); model=st.text_input("Model"); part=st.text_input("Manufacturer part number"); qty=st.number_input("Quantity",1,value=role.required_quantity); price=st.number_input("Expected unit price",0.0); supplier=st.text_input("Supplier name"); supplier_url=st.text_input("Supplier URL"); manufacturer_url=st.text_input("Manufacturer URL"); primary=st.checkbox("Make primary",value=not products); notes=st.text_area("Notes")
                    if st.form_submit_button("Add product"):
                        if not pname.strip(): st.error("Product name is required.")
                        else:
                            if primary:
                                for other in products: other.primary_product=False
                            project.products.append(ProductSelection(component_role_id=role.id,manufacturer=manufacturer,product_name=pname,model=model,manufacturer_part_number=part,quantity=int(qty),expected_unit_price=price,supplier_name=supplier,supplier_url=supplier_url,manufacturer_url=manufacturer_url,primary_product=primary,selection_status=SelectionStatus.SELECTED if primary else SelectionStatus.CANDIDATE,notes=notes))
                            try: _save(state,repository); st.rerun()
                            except Exception as error: show_repository_error(error,"saved")
        with tabs[3]:
            statuses=enum_values(RoleStatus); new_status=st.selectbox("Role status",statuses,index=statuses.index(role.current_status.value),key=f"role_status_{role.id}")
            if st.button("Update role status",key=f"update_status_{role.id}"):
                role.current_status=RoleStatus(new_status)
                try: _save(state,repository); st.rerun()
                except Exception as error: show_repository_error(error,"saved")
            impact=component_impact(project,role.id)
            st.write(f"**Affected milestones:** {', '.join(impact['milestones']) or 'None'}")
            st.write(f"**Capabilities:** {', '.join(impact['capabilities']) or 'None'}")
            st.write(f"**Subsystems:** {', '.join(impact['subsystems']) or 'None'}")
            st.write("Removing this role may block: "+(", ".join(impact['milestones']) or "no rated milestone"))
            if role.requiredness in {RoleRequiredness.OPTIONAL,RoleRequiredness.EXPERIMENTAL,RoleRequiredness.DEFERRED}:
                if st.button("Remove optional component",key=f"remove_role_{role.id}"):
                    role.current_status=RoleStatus.REMOVED
                    try: _save(state,repository); state.selected_component_id=None; st.rerun()
                    except Exception as error: show_repository_error(error,"saved")
            else: st.warning("Required components cannot be removed here because linked milestones may be affected. Change requiredness in role information first.")
