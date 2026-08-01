from datetime import datetime,timezone
from uuid import uuid4
from models.monitoring import MonitoredProductSource
from services.apify_client import ApifyService,ApifyServiceError
from repositories.apify_run_repository import ApifyRunRepository

def build_monitor_input(source:MonitoredProductSource,expected_identity:dict,run_type:str='manual')->dict:
 return {'monitoring_job_id':str(uuid4()),'project_id':source.project_id,'component_role_id':source.component_role_id,'product_id':source.product_id,'run_type':run_type,'sources':[{'source_id':source.id,'source_type':source.source_type,'url':source.source_url,'supplier':source.supplier_name,'currency':'USD','extraction':{'prefer_json_ld':True,'price_selector':None,'availability_selector':None,'shipping_selector':None,'title_selector':None,'part_number_selector':None}}],'expected_identity':expected_identity,'maximum_requests':10,'request_delay_ms':1000}
def start_monitoring_run(source,expected_identity,repository:ApifyRunRepository|None=None,service:ApifyService|None=None):
 repository=repository or ApifyRunRepository()
 active=repository.find_active_run(source.id)
 if active:raise ApifyServiceError('A monitoring run is already active for this source.')
 service=service or ApifyService();payload=build_monitor_input(source,expected_identity)
 run=service.start_task(source.apify_task_id,payload) if source.apify_task_id else service.start_actor(payload,source.apify_actor_id)
 repository.create_run(apify_run_id=run['id'],monitoring_source_id=source.id,project_id=source.project_id,component_role_id=source.component_role_id,product_id=source.product_id,run_type='manual',status=run.get('status','READY'),default_dataset_id=run.get('defaultDatasetId'),started_at=run.get('startedAt') or datetime.now(timezone.utc))
 return run
