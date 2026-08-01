import hmac,os
from datetime import datetime,timezone
from fastapi import FastAPI,Header,HTTPException,Request
from models.monitoring import ComponentProcurementState
from models.observations import ProductObservation
from repositories.apify_run_repository import ApifyRunRepository
from repositories.monitoring_repository import MonitoringRepository
from repositories.project_repository import ProjectRepository
from services.apify_client import ApifyService,ApifyServiceError
from services.component_urgency import calculate_component_urgency
from services.discovery_ingestion import ingest_discovery_candidate
from services.observation_ingestion import ingest_observation
from services.monitoring_scheduler import reconcile_source_schedule,select_monitoring_schedule
app=FastAPI(title='Robotics BOM Guardian Apify Webhook')

def _run_id(payload):return payload.get('runId') or payload.get('resource',{}).get('id') or payload.get('eventData',{}).get('actorRunId')
def _expected(project,run):
 product=next((p for p in project.products if p.elastic_product_id==run.product_id or p.manufacturer_part_number==run.product_id),None)
 return {'manufacturer':product.manufacturer if product else None,'model':product.model if product else None,'manufacturer_part_number':product.manufacturer_part_number if product else None,'title':product.product_name if product else None}
def _state(project,role_id):
 product=next((p for p in project.products if p.component_role_id==role_id and p.primary_product),None)
 return ComponentProcurementState(selected_product_id=product.elastic_product_id if product else None,purchase_status=product.purchase_status.value if product else 'Not planned',verification_status=product.verification_status.value if product else 'Unverified')
@app.post('/webhooks/apify/actor-run')
async def apify_actor_run(request:Request,x_apify_webhook_secret:str|None=Header(default=None)):
 secret=os.getenv('APIFY_WEBHOOK_SECRET')
 if not secret or not x_apify_webhook_secret or not hmac.compare_digest(secret,x_apify_webhook_secret):raise HTTPException(401,'Invalid webhook secret.')
 try:payload=await request.json()
 except Exception:raise HTTPException(400,'Malformed JSON payload.')
 event_type=payload.get('eventType') or payload.get('event_type')
 if event_type and event_type not in {'ACTOR.RUN.SUCCEEDED','ACTOR.RUN.FAILED','ACTOR.RUN.TIMED_OUT','ACTOR.RUN.ABORTED'}:raise HTTPException(400,'Unsupported Apify webhook event type.')
 run_id=_run_id(payload)
 if not run_id:raise HTTPException(400,'Apify run ID is required.')
 runs=ApifyRunRepository();record=runs.get_by_apify_run_id(run_id)
 if not record:raise HTTPException(404,'Apify run is not registered for monitoring.')
 if record.ingestion_status=='completed':return {'status':'already_processed','run_id':run_id}
 if not runs.claim_ingestion(run_id):return {'status':'already_processing','run_id':run_id}
 try:
  metadata=ApifyService().get_run(run_id);status=metadata.get('status','UNKNOWN');dataset_id=metadata.get('defaultDatasetId') or record.default_dataset_id
  if status not in {'SUCCEEDED'}:
   runs.update_run(run_id,status=status,finished_at=metadata.get('finishedAt'),error_message=metadata.get('statusMessage'),ingestion_status='failed')
   if record.monitoring_source_id:MonitoringRepository().mark_failure(record.monitoring_source_id)
   return {'status':'run_failed','run_id':run_id}
  if not dataset_id:raise ValueError('Completed run has no default dataset.')
  items=ApifyService().get_dataset_items(dataset_id);project=ProjectRepository().get_project(record.project_id)
  if not project:raise ValueError('Project no longer exists.')
  if record.run_type=='product_discovery':
   valid=invalid=0
   for item in items:
    try:ingest_discovery_candidate(item,project);valid+=1
    except Exception:invalid+=1
   runs.update_run(run_id,status=status,default_dataset_id=dataset_id,finished_at=metadata.get('finishedAt'),items_received=len(items),ingestion_status='completed' if valid else 'failed',error_message=f'{invalid} invalid discovery item(s)' if invalid else None)
   return {'status':'completed','run_id':run_id,'received':len(items),'valid':valid,'invalid':invalid,'candidates_indexed':valid}
  role=next((r for r in project.component_roles if r.id==record.component_role_id),None)
  urgency=calculate_component_urgency(project,role.id,_state(project,role.id),datetime.now(timezone.utc)) if role else None
  monitoring=MonitoringRepository();valid=invalid=quarantined=0;events=0;latest_observation=None
  for item in items:
   try:
    observation=ProductObservation.model_validate(item);latest_observation=observation;result=ingest_observation(observation,_expected(project,record),urgency.score if urgency else 0,monitoring_repository=monitoring);valid+=1;quarantined+=int(result.get('quarantined',False));events+=len(result.get('events',[]))
   except Exception:invalid+=1
  runs.update_run(run_id,status=status,default_dataset_id=dataset_id,finished_at=metadata.get('finishedAt'),items_received=len(items),ingestion_status='completed' if valid else 'failed',error_message=f'{invalid} invalid dataset item(s)' if invalid else None)
  if record.monitoring_source_id and role and latest_observation:
   source=monitoring.get_source(record.monitoring_source_id)
   if source:
    last=latest_observation;state=_state(project,role.id);state.availability=last.commercial.availability.value;state.expected_delivery_date=last.commercial.delivery_latest;state.last_observation_at=last.observed_at
    updated_urgency=calculate_component_urgency(project,role.id,state,datetime.now(timezone.utc));preference=monitoring.get_preference(project.id,role.id);decision=select_monitoring_schedule(updated_urgency,state,preference,source.consecutive_failures,source.monitoring_tier)
    if decision.changed:reconcile_source_schedule(source,decision,source.apify_actor_id or os.getenv('APIFY_PRODUCT_MONITOR_ACTOR_ID',''),source.apify_task_id,monitoring,ApifyService())
  return {'status':'completed','run_id':run_id,'received':len(items),'valid':valid,'invalid':invalid,'quarantined':quarantined,'change_events':events}
 except (ApifyServiceError,ValueError) as error:
  runs.update_run(run_id,ingestion_status='failed',error_message=str(error));raise HTTPException(502,str(error))
 except Exception:
  runs.update_run(run_id,ingestion_status='failed',error_message='Ingestion service failure.');raise HTTPException(503,'Observation ingestion is temporarily unavailable.')
