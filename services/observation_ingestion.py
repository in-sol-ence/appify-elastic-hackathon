import hashlib
from datetime import datetime,timezone
from elasticsearch import ConflictError,NotFoundError
from models.observations import ExtractionStatus,ProductObservation
from services.change_severity import evaluate_change_severity
from services.elasticsearch_client import CHANGE_EVENTS_INDEX,CURRENT_LISTINGS_INDEX,OBSERVATIONS_INDEX,QUARANTINE_INDEX,SOURCE_HEALTH_INDEX,get_elasticsearch_client,require_write_access
from services.product_change_detection import _event,detect_changes,observation_id
from services.product_identity import verify_product_identity

def current_document_id(product_id,source_id):return hashlib.sha256(f'{product_id}|{source_id}'.encode()).hexdigest()
def _document(observation):
 data=observation.model_dump(mode='json');data['@timestamp']=data.pop('observed_at');data['observation_id']=observation_id(observation);return data
def _previous(client,observation):
 try:
  source=client.get(index=CURRENT_LISTINGS_INDEX,id=current_document_id(observation.product_id,observation.source_id))['_source'];source['observed_at']=source.pop('@timestamp');source.pop('observation_id',None);return ProductObservation.model_validate(source)
 except NotFoundError:return None
def ingest_observation(observation:ProductObservation,expected_identity:dict,urgency_score:float=0,client=None,monitoring_repository=None):
 require_write_access();client=client or get_elasticsearch_client();doc=_document(observation);oid=doc['observation_id']
 try:client.create(index=OBSERVATIONS_INDEX,id=oid,document=doc)
 except ConflictError:return {'duplicate':True,'observation_id':oid,'events':[]}
 verified,method=verify_product_identity(observation,expected_identity)
 if observation.extraction.status!=ExtractionStatus.FAILED and not verified:
  client.index(index=QUARANTINE_INDEX,id=oid,document=doc|{'quarantine_reason':method});
  if monitoring_repository:monitoring_repository.mark_failure(observation.source_id)
  return {'duplicate':False,'quarantined':True,'observation_id':oid,'events':[]}
 previous=_previous(client,observation)
 if previous and observation.extraction.status!=ExtractionStatus.FAILED and observation.observed_at<=previous.observed_at:
  return {'duplicate':False,'out_of_order':True,'observation_id':oid,'events':[]}
 try:previous_health=client.get(index=SOURCE_HEALTH_INDEX,id=observation.source_id)['_source']
 except NotFoundError:previous_health={}
 events=detect_changes(previous,observation,repeated_missing_count=int(previous_health.get('consecutive_failures',0)))
 if observation.extraction.status!=ExtractionStatus.FAILED and int(previous_health.get('consecutive_failures',0))>0:
  events.append(_event(observation,'source_recovered','failed','success'))
 if observation.extraction.status==ExtractionStatus.FAILED:
  if monitoring_repository:monitoring_repository.mark_failure(observation.source_id)
 else:
  client.index(index=CURRENT_LISTINGS_INDEX,id=current_document_id(observation.product_id,observation.source_id),document=doc)
  if monitoring_repository:monitoring_repository.mark_success(observation.source_id,observation.observed_at)
 for event in events:
  severity=evaluate_change_severity(event.event_type,urgency_score,event.change_magnitude or 0,event.source_confidence);event.component_urgency_score=urgency_score;event.event_severity=severity.severity
  client.create(index=CHANGE_EVENTS_INDEX,id=event.event_id,document=event.model_dump(mode='json'))
 failure_count=(int(previous_health.get('consecutive_failures',0))+1) if observation.extraction.status==ExtractionStatus.FAILED else 0
 health={'source_id':observation.source_id,'last_successful_run':observation.observed_at.isoformat() if observation.extraction.status!=ExtractionStatus.FAILED else previous_health.get('last_successful_run'),'last_failure':observation.observed_at.isoformat() if observation.extraction.status==ExtractionStatus.FAILED else previous_health.get('last_failure'),'consecutive_failures':failure_count,'extraction_confidence':observation.extraction.confidence,'last_verified_observation':observation.observed_at.isoformat() if verified else None,'data_freshness_status':'fresh' if observation.extraction.status!=ExtractionStatus.FAILED else 'stale','actor_run_id':observation.actor_run_id,'error_category':observation.extraction.error_category}
 client.index(index=SOURCE_HEALTH_INDEX,id=observation.source_id,document=health)
 return {'duplicate':False,'quarantined':False,'observation_id':oid,'events':events}
