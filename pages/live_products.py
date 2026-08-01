import os
from datetime import datetime,timezone
from urllib.parse import urlparse
from uuid import uuid4
import streamlit as st
from models.enums import RoleRequiredness
from models.monitoring import ComponentProcurementState,MonitoringPreference
from repositories.apify_run_repository import ApifyRunRepository
from repositories.monitoring_repository import MonitoringRepository
from services.apify_availability import check_product_availability
from services.apify_run_service import start_monitoring_run
from services.change_event_store import acknowledge_change,recent_changes
from services.component_urgency import calculate_component_urgency
from services.elasticsearch_client import ProductSearchError
from services.historical_product_analysis import analyze_product_history,current_product_states
from services.monitoring_scheduler import select_monitoring_schedule
from services.procurement_recommendation import recommend_procurement
from services.product_driver_discovery import discover_product_drivers
from services.apify_client import ApifyServiceError
from services.source_health import delivery_fit,freshness

def _selected(project,role_id):return next((p for p in project.products if p.component_role_id==role_id and p.primary_product),None) or next((p for p in project.products if p.component_role_id==role_id and p.selection_status.value=='Selected'),None)
def _approved(url):
 host=(urlparse(url).hostname or '').lower();domains=[x.strip().lower() for x in os.getenv('APPROVED_PRODUCT_DOMAINS','').split(',') if x.strip()]
 return urlparse(url).scheme in {'http','https'} and any(host==d or host.endswith('.'+d) for d in domains)
def _state(product,docs):
 latest=docs[0] if docs else {};commercial=latest.get('commercial',{});delivery=commercial.get('delivery_latest');dt=datetime.fromisoformat(delivery.replace('Z','+00:00')) if delivery else None
 availability_order={'in_stock':6,'limited_stock':5,'preorder':4,'backorder':3,'unknown':2,'out_of_stock':1,'discontinued':0};best=max((d.get('commercial',{}).get('availability','unknown') for d in docs),key=lambda value:availability_order.get(value,2),default='unknown')
 return ComponentProcurementState(availability=best,expected_delivery_date=dt,last_observation_at=datetime.fromisoformat(latest['@timestamp'].replace('Z','+00:00')) if latest.get('@timestamp') else None,source_confidence=latest.get('extraction',{}).get('confidence',0),active_sellers=sum(d.get('commercial',{}).get('availability')=='in_stock' for d in docs),selected_product_id=product.elastic_product_id if product else None,purchase_status=product.purchase_status.value if product else 'Not planned',verification_status=product.verification_status.value if product else 'Unverified')
def render(project,report,repository):
 from ui.shared import get_wizard
 app_state=get_wizard();st.subheader('Live Products');st.caption('Live collection uses approved sources only. PostgreSQL remains the project source of truth.')
 monitoring=MonitoringRepository();runs=ApifyRunRepository()
 try:sources=monitoring.list_sources(project.id)
 except Exception as error:st.error(f'Monitoring configuration unavailable: {error}');return
 try:docs=current_product_states(project.id)
 except Exception:docs=[];st.warning('Live Elasticsearch state is unavailable. Project and BOM functions remain available.')
 by_product={}
 for doc in docs:by_product.setdefault(doc.get('product_id'),[]).append(doc)
 rows=[];contexts={}
 for role in project.component_roles:
  product=_selected(project,role.id);product_docs=by_product.get(product.elastic_product_id if product else None,[]);state=_state(product,product_docs);urgency=calculate_component_urgency(project,role.id,state);tier=next((s.monitoring_tier for s in sources if s.component_role_id==role.id),urgency.level);fresh=freshness(state.last_observation_at,tier);fit,margin=delivery_fit(role.required_by,state.expected_delivery_date,role.integration_risk,state.integration_buffer_days);previous=app_state.editing_state.get(f'live_recommendation_{role.id}');rec=recommend_procurement(urgency,'Compatible' if product and product.verification_status.value!='Failed' else 'Insufficient information',state.availability,fit,alternatives=sum(p.component_role_id==role.id and not p.primary_product for p in project.products),purchase_status=state.purchase_status,verification_status=state.verification_status,freshness=fresh,optional=role.requiredness==RoleRequiredness.OPTIONAL,previous_action=previous);app_state.editing_state[f'live_recommendation_{role.id}']=rec.action
  contexts[role.id]=(product,state,urgency,tier,fresh,fit,rec,product_docs)
  rows.append({'Role':role.role_name,'Selected product':product.product_name if product else 'Not selected','Required by':role.required_by,'Criticality':max([r.rating for r in project.role_milestone_ratings if r.component_role_id==role.id],default=0),'Urgency':f'{urgency.level} ({urgency.score:.1f})','Best availability':state.availability,'Delivery fit':fit,'Recommendation':rec.action.replace('_',' ').title(),'Last checked':state.last_observation_at or 'Never','Data freshness':fresh,'_id':role.id,'_score':urgency.score})
 rows.sort(key=lambda x:x['_score'],reverse=True);st.dataframe([{k:v for k,v in row.items() if not k.startswith('_')} for row in rows],hide_index=True,use_container_width=True)
 role_id=st.selectbox('Component monitoring detail',[r['_id'] for r in rows],format_func=lambda value:next(r.role_name for r in project.component_roles if r.id==value),key='live_role');role=next(r for r in project.component_roles if r.id==role_id);product,state,urgency,tier,fresh,fit,rec,product_docs=contexts[role_id]
 st.markdown(f'### {role.role_name}');st.write(f'**Required milestone:** {project.entity_names().get(role.first_required_milestone_id,"Not assigned")} · **Required by:** {role.required_by or "Unknown"} · **Urgency:** {urgency.level} {urgency.score:.1f}/100');st.write('\n'.join(f'- {x}' for x in urgency.explanation));st.write(f'**Recommendation: {rec.action.replace("_"," ").title()}** — {rec.reason}');
 if rec.change_explanation:st.info('\n'.join(rec.change_explanation))
 st.markdown('#### Current product state')
 if product:
  st.write(f'{product.product_name} · {state.availability} · Delivery {fit} · Freshness {fresh}')
  product_url=st.text_input('Product URL to check with Apify',value=product.supplier_url or product.manufacturer_url,key=f'apify_product_url_{role_id}',help='This runs the project product-page Actor once and reads schema.org product availability from the page.')
  if st.button('Check URL availability',key=f'apify_availability_{role_id}',type='primary'):
   try:
    with st.spinner('Apify is checking the product page...'):
     app_state.editing_state[f'apify_availability_result_{role_id}']=check_product_availability(product_url,product.supplier_name)
   except Exception as error:st.error(f'Apify availability check failed: {error}')
  availability_result=app_state.editing_state.get(f'apify_availability_result_{role_id}')
  if availability_result and availability_result.get('url')==product_url:
   if availability_result.get('status')=='success':
    price=availability_result.get('price');currency=availability_result.get('currency') or ''
    st.success(f"Availability: {availability_result['availability'].replace('_',' ').title()}"+(f" · Price: {currency} {price}" if price is not None else ''))
   else:st.warning(f"Apify could not read availability from this page: {availability_result.get('error') or 'No structured product data found.'}")
   st.caption(f"Apify run {availability_result.get('run_id') or 'unknown'} · checked {availability_result.get('checked_at') or 'just now'} · confidence {availability_result.get('confidence',0):.0%}")
 else:st.warning('No selected product. Select a compatible catalog product first.')
 st.markdown('#### GitHub drivers and integrations')
 st.caption('Uses the dedicated GitHub Driver Finder Apify Actor. Matches are unverified candidates, not proof of compatibility or safety.')
 driver_key=f'github_driver_candidates_{product.id}' if product else None
 if st.button('Check GitHub for drivers with Apify',key=f'check_drivers_{role.id}',disabled=not product,use_container_width=True):
  with st.spinner('The GitHub Driver Finder Actor is checking repositories...'):
   try:
    candidates=discover_product_drivers(product.product_name,product.manufacturer,product.model,project.id,role.id,product.elastic_product_id or product.id);app_state.editing_state[driver_key]=candidates;st.success(f'Found {len(candidates)} unverified driver or integration candidate(s).')
   except ApifyServiceError as error:st.error(str(error))
 if product:
  for index,candidate in enumerate(app_state.editing_state.get(driver_key,[])):
   with st.container(border=True):
    st.write(f"**{candidate.get('repository_full_name') or candidate.get('repository_name')}** · ★ {candidate.get('stars',0)} · {candidate.get('language','Unknown')}");st.write(candidate.get('description') or 'No description provided.');st.caption(f"Updated: {candidate.get('updated_at') or 'Unknown'} · {'Archived' if candidate.get('archived') else 'Active repository'} · Candidate unverified");st.link_button('Open GitHub repository',candidate['repository_url'],key=f'github_driver_link_{role.id}_{index}')
 role_sources=[s for s in sources if s.component_role_id==role_id]
 st.markdown('#### Monitoring sources')
 for source in role_sources:
  with st.container(border=True):
   st.write(f'**{source.supplier_name or source.source_url}** · {source.monitoring_tier} · {"Enabled" if source.monitoring_enabled else "Disabled"}');st.caption(f'Last observation: {source.last_observation_at or "Never"} · failures: {source.consecutive_failures}')
   c1,c2=st.columns(2)
   if c1.button('Refresh now',key=f'refresh_{source.id}',disabled=not source.monitoring_enabled):
    try:
     expected={'manufacturer':product.manufacturer if product else None,'model':product.model if product else None,'manufacturer_part_number':product.manufacturer_part_number if product else None,'title':product.product_name if product else None};run=start_monitoring_run(source,expected,runs);st.success(f"Collection started. Apify run: {run['id']}")
    except Exception as error:st.error(str(error))
   if c2.button('Disable source' if source.monitoring_enabled else 'Enable source',key=f'toggle_{source.id}'):
    try:monitoring.set_enabled(source.id,not source.monitoring_enabled);st.rerun()
    except Exception as error:st.error(str(error))
 if product:
  with st.expander('Add monitoring source'):
   with st.form('add_live_source'):
    url=st.text_input('Approved product URL');supplier=st.text_input('Supplier name');task=st.text_input('Apify Task ID (optional)')
    if st.form_submit_button('Add source'):
     if not _approved(url):st.error('Source domain is not in APPROVED_PRODUCT_DOMAINS.')
     else:
      try:monitoring.create_source(project.id,role.id,product.elastic_product_id or product.manufacturer_part_number or product.id,url,supplier,task_id=task or None,actor_id=os.getenv('APIFY_PRODUCT_MONITOR_ACTOR_ID'));st.rerun()
      except Exception as error:st.error(str(error))
 st.markdown('#### Monitoring frequency')
 pref=monitoring.get_preference(project.id,role.id);decision=select_monitoring_schedule(urgency,state,pref,current_tier=tier);st.write(f'{decision.tier}: every {decision.frequency_hours} hour(s). {decision.reason}')
 override=st.number_input('User override frequency (hours, 0 for automatic)',min_value=0,value=pref.user_override_frequency_hours if pref and pref.user_override_frequency_hours else 0,key='live_override')
 if st.button('Save frequency preference',key='save_live_frequency'):
  preference=pref or MonitoringPreference(id=str(uuid4()),project_id=project.id,component_role_id=role.id);preference.user_override_frequency_hours=override or None;monitoring.save_preference(preference);st.success('Monitoring preference saved.')
 st.markdown('#### Recent changes')
 try:
  changes=recent_changes(project.id,role.id)
  if not changes:st.caption('No change events recorded.')
  for change in changes[:10]:
   st.write(f"**{change['event_type'].replace('_',' ').title()}** · {change.get('event_severity','Unknown')} · {change.get('observed_at')}")
   if change.get('acknowledgment_status')!='acknowledged' and st.button('Acknowledge',key=f"ack_{change['event_id']}"):
    try:acknowledge_change(change['event_id']);st.rerun()
    except Exception as error:st.error(str(error))
 except Exception:st.caption('Change history is unavailable.')
 if product and st.button('View historical observations',key='live_history'):
  try:st.json(analyze_product_history(product.elastic_product_id or product.manufacturer_part_number))
  except Exception:st.error('Historical product analysis is temporarily unavailable.')
