import os
from decimal import Decimal
from functools import lru_cache
from typing import Any
from apify_client import ApifyClient
from apify_client.errors import ApifyApiError
from dotenv import load_dotenv
load_dotenv()
class ApifyServiceError(RuntimeError):pass
class ApifyAuthenticationError(ApifyServiceError):pass
class ApifyRateLimitError(ApifyServiceError):pass
class ApifyRunError(ApifyServiceError):pass

def _token():
 token=os.getenv('APIFY_API_TOKEN') or os.getenv('APIFY_TOKEN')
 if not token:raise ApifyAuthenticationError('Apify is not configured. Add APIFY_API_TOKEN to .env.')
 return token
@lru_cache(maxsize=1)
def get_apify_client()->ApifyClient:return ApifyClient(_token())
def _translate(error:Exception)->ApifyServiceError:
 status=getattr(error,'status_code',None)
 if status in {401,403}:return ApifyAuthenticationError('Apify authentication failed.')
 if status==429:return ApifyRateLimitError('Apify rate limit reached. Try again later.')
 return ApifyServiceError('Apify request failed.')
def _webhooks():
 base=os.getenv('APIFY_WEBHOOK_BASE_URL');secret=os.getenv('APIFY_WEBHOOK_SECRET')
 if not base or not secret:return None
 return [{'eventTypes':['ACTOR.RUN.SUCCEEDED','ACTOR.RUN.FAILED','ACTOR.RUN.TIMED_OUT','ACTOR.RUN.ABORTED'],'requestUrl':base.rstrip('/')+'/webhooks/apify/actor-run','payloadTemplate':'{\"eventType\":\"{{eventType}}\",\"resource\":{{resource}}}','headersTemplate':'{\"X-Apify-Webhook-Secret\":\"'+secret+'\"}'}]
class ApifyService:
 def __init__(self,client:ApifyClient|None=None):self.client=client or get_apify_client()
 def start_actor(self,run_input:dict,actor_id:str|None=None)->dict:
  actor_id=actor_id or os.getenv('APIFY_PRODUCT_MONITOR_ACTOR_ID')
  if not actor_id:raise ApifyServiceError('APIFY_PRODUCT_MONITOR_ACTOR_ID is missing.')
  try:return self.client.actor(actor_id).start(run_input=run_input,build=os.getenv('APIFY_DEFAULT_BUILD','latest'),max_total_charge_usd=Decimal(os.getenv('APIFY_MAX_RUN_COST_USD','1.00')),webhooks=_webhooks())
  except ApifyApiError as error:raise _translate(error) from error
 def start_task(self,task_id:str,run_input:dict)->dict:
  try:return self.client.task(task_id).start(task_input=run_input,build=os.getenv('APIFY_DEFAULT_BUILD','latest'),webhooks=_webhooks())
  except ApifyApiError as error:raise _translate(error) from error
 def get_run(self,run_id:str)->dict:
  try:
   run=self.client.run(run_id).get()
   if not run:raise ApifyRunError('Apify run does not exist.')
   return run
  except ApifyApiError as error:raise _translate(error) from error
 def call_actor_and_get_items(self,actor_id:str,run_input:dict,timeout_secs:int=120,limit:int=100)->tuple[dict,list[dict]]:
  try:
   run=self.client.actor(actor_id).call(run_input=run_input,build=os.getenv('APIFY_DEFAULT_BUILD','latest'),max_total_charge_usd=Decimal(os.getenv('APIFY_MAX_RUN_COST_USD','1.00')),timeout_secs=timeout_secs,wait_secs=timeout_secs)
   if not run:raise ApifyRunError('Apify analysis did not return a run.')
   if run.get('status')!='SUCCEEDED':raise ApifyRunError(f"Apify analysis ended with status {run.get('status','unknown')}.")
   dataset_id=run.get('defaultDatasetId')
   if not dataset_id:raise ApifyRunError('Apify analysis did not produce a dataset.')
   return run,self.get_dataset_items(dataset_id,limit)
  except ApifyApiError as error:raise _translate(error) from error
 def get_dataset_items(self,dataset_id:str,limit:int=1000)->list[dict]:
  try:return list(self.client.dataset(dataset_id).list_items(clean=True,limit=limit).items)
  except ApifyApiError as error:raise ApifyServiceError('Apify dataset retrieval failed.') from error
 def abort_run(self,run_id:str)->dict:
  try:return self.client.run(run_id).abort()
  except ApifyApiError as error:raise _translate(error) from error
 def create_task(self,name:str,actor_id:str,task_input:dict)->dict:
  try:return self.client.tasks().create(actor_id=actor_id,name=name,task_input=task_input)
  except ApifyApiError as error:raise _translate(error) from error
 def create_schedule(self,name:str,cron_expression:str,actions:list[dict])->dict:
  try:return self.client.schedules().create(name=name,cron_expression=cron_expression,is_enabled=True,is_exclusive=True,actions=actions)
  except ApifyApiError as error:raise _translate(error) from error
 def update_schedule(self,schedule_id:str,cron_expression:str,actions:list[dict])->dict:
  try:return self.client.schedule(schedule_id).update(cron_expression=cron_expression,actions=actions,is_enabled=True)
  except ApifyApiError as error:raise _translate(error) from error

def test_apify_connection(service:ApifyService|None=None)->dict:
 service=service or ApifyService();actor_id=os.getenv('APIFY_PRODUCT_MONITOR_ACTOR_ID')
 try:
  user=service.client.user().get();actor=service.client.actor(actor_id).get() if actor_id else None
  datasets=service.client.datasets().list(limit=1)
  return {'authenticated':bool(user),'user_id':(user or {}).get('id'),'actor_exists':bool(actor),'datasets_accessible':datasets is not None}
 except ApifyApiError as error:raise _translate(error) from error
