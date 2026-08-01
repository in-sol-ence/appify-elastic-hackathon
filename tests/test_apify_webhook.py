import asyncio
from datetime import datetime,timezone
import pytest
from fastapi import HTTPException
import api.apify_webhook as webhook
from models.monitoring import ApifyRunRecord
from services.templates import build_sample_project

class Request:
 def __init__(self,payload):self.payload=payload
 async def json(self):return self.payload
class Runs:
 status='pending';updates=[]
 def get_by_apify_run_id(self,id):
  project=Projects.project
  return ApifyRunRecord(id='i',apify_run_id=id,project_id=project.id,component_role_id=project.component_roles[0].id,product_id='x',run_type='manual',status='SUCCEEDED',default_dataset_id='d',ingestion_status=self.status)
 def claim_ingestion(self,id):return True
 def update_run(self,*args,**kwargs):self.updates.append((args,kwargs))
class Apify:
 def get_run(self,id):return {'id':id,'status':'SUCCEEDED','defaultDatasetId':'d'}
 def get_dataset_items(self,id):return [{'schema_version':'1.0','monitoring_job_id':'j','project_id':Projects.project.id,'component_role_id':Projects.project.component_roles[0].id,'product_id':'x','source_id':'s','actor_run_id':'run','observed_at':datetime.now(timezone.utc).isoformat(),'source_type':'supplier_product_page','source_url':'https://example.com','identity':{},'commercial':{'availability':'unknown'},'product_state':{},'evidence':{},'extraction':{'status':'failed','confidence':0,'warnings':[]}}]
class Projects:
 project=build_sample_project()
 def get_project(self,id):return self.project
class Monitoring:pass

def setup(monkeypatch,status='pending'):
 monkeypatch.setenv('APIFY_WEBHOOK_SECRET','secret');runs=Runs();runs.status=status;runs.updates=[]
 monkeypatch.setattr(webhook,'ApifyRunRepository',lambda:runs);monkeypatch.setattr(webhook,'ApifyService',Apify);monkeypatch.setattr(webhook,'ProjectRepository',Projects);monkeypatch.setattr(webhook,'MonitoringRepository',Monitoring);monkeypatch.setattr(webhook,'ingest_observation',lambda *args,**kwargs:{'events':[]});return runs
def call(secret='secret'):return asyncio.run(webhook.apify_actor_run(Request({'runId':'run'}),secret))
def test_invalid_secret(monkeypatch):
 setup(monkeypatch)
 with pytest.raises(HTTPException) as error:call('bad')
 assert error.value.status_code==401
def test_duplicate_webhook(monkeypatch):setup(monkeypatch,'completed');assert call()['status']=='already_processed'
def test_valid_webhook_retrieves_dataset_and_updates_run(monkeypatch):
 runs=setup(monkeypatch);result=call();assert result['received']==1 and runs.updates
