import os
import streamlit as st

from models.products import EvidenceFilters
from models.search import ProductSearchResult
from repositories.project_repository import ProjectRepository
from services.apify_product_analysis import analyze_product_with_apify
from services.compatibility import evaluate_product_compatibility
from services.elasticsearch_client import ProductSearchError
from services.product_evidence_search import search_product_evidence
from services.product_search import find_similar_products, search_products
from services.product_selection import apply_catalog_product, reject_catalog_product
from services.search_profile import build_component_search_profile
from ui.persistence import save_wizard_project, show_repository_error
from ui.shared import get_wizard

REJECTION_REASONS=["Technically incompatible","Too expensive","Missing documentation","Difficult integration","Wrong form factor","Insufficient information","User preference","Other"]


def _priority(project,report,role):
    ratings=[r.rating for r in project.role_milestone_ratings if r.component_role_id==role.id]
    missing=not any(p.component_role_id==role.id and (p.primary_product or p.selection_status.value=="Selected") for p in project.products)
    blocked=report.component_roles[role.id].status.value=="Blocked"
    return (role.requiredness.value=="Mandatory" and missing,blocked,max(ratings,default=0),role.necessity_confidence)


def _known_specs(product):
    fields=["input_voltage_min_v","input_voltage_max_v","continuous_current_per_channel_a","peak_current_per_channel_a","channel_count","control_interfaces","communication_interfaces","supported_operating_systems","supported_software","power_w","weight_g","length_mm","width_mm","height_mm"]
    return {field.replace('_',' ').title():getattr(product,field) for field in fields if getattr(product,field) not in (None,[],"")}


def _save_selection(project,product,role_id,repository,state,primary=True):
    fresh=repository.get_project(state.project_id) if state.project_id else project
    if fresh is None:raise ValueError("The selected PostgreSQL project no longer exists.")
    selection,readiness=apply_catalog_product(fresh,role_id,product,primary)
    state.project=fresh;state.selected_project=fresh;state.readiness_result=readiness
    save_wizard_project(state,repository,state.persistence_status if state.persistence_status in {"draft","active","archived"} else "active")
    return selection


def _render_apify_analysis(analysis):
    st.markdown("#### Apify product analysis")
    st.caption(f"Actor: {analysis['actor_id']} · Run: {analysis.get('run_id') or 'unknown'}")
    st.write("**Evidence query:**",analysis["query"])
    for index,source in enumerate(analysis["sources"]):
        with st.container(border=True):
            st.write(source["title"])
            if source["description"]:st.caption(source["description"])
            st.link_button("Open source",source["url"],key=f"analysis_source_{analysis.get('run_id')}_{index}")
    with st.expander("Actor dataset output"):
        st.json(analysis["raw_output"])


def render(project,report,repository:ProjectRepository)->None:
    state=get_wizard();st.subheader("Find Products")
    roles=sorted(project.component_roles,key=lambda role:_priority(project,report,role),reverse=True)
    if not roles:st.info("Add component roles before searching for products.");return
    role_id=st.selectbox("Find products for",[r.id for r in roles],format_func=lambda item:next(r.role_name for r in roles if r.id==item),key="find_role")
    try:profile=build_component_search_profile(project,role_id)
    except ValueError as error:st.error(str(error));return
    st.markdown("#### Search profile")
    st.write(f"**Role:** {profile.role_name} · **Required milestone:** {profile.required_milestone or 'Not assigned'} · **Criticality:** {profile.criticality}/5")
    st.write("**Hard requirements**");st.markdown("\n".join(f"- {r.description}" for r in profile.hard_requirements) or "- None")
    st.write("**Preferences**");st.markdown("\n".join(f"- {r.description}" for r in profile.preferred_requirements) or "- None")
    st.write(f"**Connected components:** {', '.join(profile.connected_components) or 'None'}")
    request_text=st.text_area("Search description",profile.natural_language_description,key=f"find_query_{role_id}")
    left,right=st.columns(2)
    if left.button("Search Products",type="primary",key="find_search"):
        try:
            edited=profile.model_copy(update={"natural_language_description":request_text});results=search_products(edited)
            state.editing_state["product_results"]=[r.model_dump(mode="json") for r in results];state.editing_state["product_profile"]=edited.model_dump(mode="json")
            state.editing_state["compare_products"]=[]
            if not results:st.info("No indexed products met all hard requirements.")
        except ProductSearchError as error:st.error(str(error))
    if right.button("Reset Search",key="find_reset"):
        state.editing_state.pop("product_results",None);state.editing_state.pop("product_profile",None);st.rerun()
    raw=state.editing_state.get("product_results",[]);results=[ProductSearchResult.model_validate(item) for item in raw]
    if os.getenv("INCLUDE_DEVELOPMENT_PRODUCTS")!="1":results=[result for result in results if result.product.source_type!="development_sample"]
    if not results:return
    st.markdown("#### Search results")
    compare=[]
    for result in results:
        product=result.product;evaluation=evaluate_product_compatibility(profile,product)
        with st.container(border=True):
            st.markdown(f"### {product.name}");st.write(f"{product.manufacturer} · {product.model or 'No model'} · Source: {product.source_type.replace('_',' ')}")
            if product.source_type=="development_sample":st.warning("Development sample — not a real purchasable product.")
            elif product.source_url:st.caption(f"Observed source: {product.source_url}")
            st.write(f"**{evaluation.status}** · Project fit **{result.project_fit_score:.1f}/100** · Search relevance {result.search_score:.2f}")
            st.write(_known_specs(product));st.write(f"Estimated price: {'Unknown' if product.price_estimate is None else f'{product.currency or ""} {product.price_estimate:,.2f}'} · Documentation: {'Yes' if product.documentation_available else 'Unknown/No'}")
            with st.expander("Compatibility and product details"):
                st.write("**Passed:** "+("; ".join(evaluation.passed_requirements) or "None"));st.write("**Failed:** "+("; ".join(evaluation.failed_requirements) or "None"));st.write("**Unknown:** "+("; ".join(evaluation.unknown_requirements) or "None"));st.write("**Score breakdown:**",result.score_explanation)
                evidence_query=st.text_input("Evidence question",value=request_text,key=f"evidence_query_{product.product_id}")
                if st.button("Search evidence",key=f"evidence_{product.product_id}"):
                    try:
                        evidence=search_product_evidence(product.product_id,evidence_query,EvidenceFilters())
                        if not evidence:st.info("No local evidence matched this question.")
                        for item in evidence:st.write(f"**{item.title}** · {item.source_type} · authority {item.source_authority:.2f}\n\n{item.text}\n\n{item.source_url}")
                    except ProductSearchError as error:st.error(str(error))
            actions=st.columns(6)
            if actions[0].button("Select product",key=f"select_{product.product_id}"):
                try:_save_selection(project,product,role_id,repository,state,True);st.success("Product selected and saved to PostgreSQL.");st.rerun()
                except Exception as error:show_repository_error(error,"saved")
            if actions[1].button("Add candidate",key=f"candidate_{product.product_id}"):
                try:_save_selection(project,product,role_id,repository,state,False);st.success("Candidate saved.");st.rerun()
                except Exception as error:show_repository_error(error,"saved")
            if actions[2].button("Find similar",key=f"similar_{product.product_id}"):
                try:
                    similar=find_similar_products(product.product_id,profile);state.editing_state["product_results"]=[r.model_dump(mode="json") for r in similar];st.rerun()
                except ProductSearchError as error:st.error(str(error))
            analysis_key=f"apify_analysis_{product.product_id}"
            if actions[3].button("Analyze",key=f"analyze_{product.product_id}",help="Run Apify's Google Search Results Scraper for product evidence"):
                try:
                    with st.spinner("Apify is analyzing this product..."):
                        state.editing_state[analysis_key]=analyze_product_with_apify(product,profile)
                except Exception as error:st.error(str(error))
            reason=actions[4].selectbox("Reject reason",REJECTION_REASONS,key=f"reason_{product.product_id}",label_visibility="collapsed")
            if actions[5].button("Reject",key=f"reject_{product.product_id}"):
                try:
                    fresh=repository.get_project(state.project_id) if state.project_id else project;reject_catalog_product(fresh,role_id,product,reason);state.project=fresh;state.selected_project=fresh;save_wizard_project(state,repository,state.persistence_status if state.persistence_status in {"draft","active","archived"} else "active");st.rerun()
                except Exception as error:show_repository_error(error,"saved")
            if state.editing_state.get(analysis_key):_render_apify_analysis(state.editing_state[analysis_key])
            if st.checkbox("Compare",key=f"compare_{product.product_id}") and len(compare)<4:compare.append(result)
    if compare:
        st.markdown("#### Product comparison")
        rows=[]
        fields=[("Compatibility status",lambda r:r.compatibility_status),("Voltage support",lambda r:f"{r.product.input_voltage_min_v or 'Unknown'}–{r.product.input_voltage_max_v or 'Unknown'} V"),("Continuous current",lambda r:r.product.continuous_current_per_channel_a or "Unknown"),("Peak current",lambda r:r.product.peak_current_per_channel_a or "Unknown"),("Channel count",lambda r:r.product.channel_count or "Unknown"),("Interfaces",lambda r:", ".join(r.product.control_interfaces) or "Unknown"),("Operating systems",lambda r:", ".join(r.product.supported_operating_systems) or "Unknown"),("Software",lambda r:", ".join(r.product.supported_software) or "Unknown"),("Documentation",lambda r:"Yes" if r.product.documentation_available else "Unknown"),("Price",lambda r:r.product.price_estimate if r.product.price_estimate is not None else "Unknown"),("Project-fit score",lambda r:r.project_fit_score),("Unknown specifications",lambda r:", ".join(r.missing_fields) or "None")]
        for label,getter in fields:rows.append({"Specification":label,**{r.product.name:getter(r) for r in compare}})
        st.dataframe(rows,hide_index=True,use_container_width=True)
