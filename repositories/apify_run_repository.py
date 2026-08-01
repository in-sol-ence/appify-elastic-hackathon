from uuid import UUID,uuid4
import psycopg
from models.monitoring import ApifyRunRecord
from repositories.database import get_connection
from repositories.exceptions import RepositoryError
class ApifyRunRepository:
 def __init__(self,database_url=None):self.database_url=database_url
 def create_run(self,**values):
  rid=uuid4()
  with get_connection(self.database_url) as c:
   row=c.execute('''INSERT INTO apify_runs(id,apify_run_id,monitoring_source_id,project_id,component_role_id,product_id,run_type,status,default_dataset_id,started_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(apify_run_id) DO UPDATE SET updated_at=CURRENT_TIMESTAMP RETURNING *''',(rid,values['apify_run_id'],UUID(values['monitoring_source_id']) if values.get('monitoring_source_id') else None,UUID(values['project_id']),UUID(values['component_role_id']) if values.get('component_role_id') else None,values.get('product_id'),values['run_type'],values['status'],values.get('default_dataset_id'),values.get('started_at'))).fetchone()
  return self._model(row)
 def _model(self,row):
  if not row:return None
  data=dict(row)
  for key in ['id','monitoring_source_id','project_id','component_role_id']:
   if data.get(key):data[key]=str(data[key])
  return ApifyRunRecord.model_validate(data)
 def get_by_apify_run_id(self,run_id):
  with get_connection(self.database_url) as c:row=c.execute('SELECT * FROM apify_runs WHERE apify_run_id=%s',(run_id,)).fetchone()
  return self._model(row)
 def find_active_run(self,source_id):
  with get_connection(self.database_url) as c:row=c.execute("SELECT * FROM apify_runs WHERE monitoring_source_id=%s AND status IN ('READY','RUNNING') ORDER BY created_at DESC LIMIT 1",(UUID(source_id),)).fetchone()
  return self._model(row)
 def update_run(self,run_id,**values):
  allowed={'status','default_dataset_id','finished_at','items_received','error_message','ingestion_status'};parts=[];params=[]
  for key,value in values.items():
   if key in allowed:parts.append(f'{key}=%s');params.append(value)
  if not parts:return
  params.append(run_id)
  with get_connection(self.database_url) as c:c.execute(f"UPDATE apify_runs SET {','.join(parts)},updated_at=CURRENT_TIMESTAMP WHERE apify_run_id=%s",params)
 def claim_ingestion(self,run_id):
  with get_connection(self.database_url) as c:
   row=c.execute("UPDATE apify_runs SET ingestion_status='processing',updated_at=CURRENT_TIMESTAMP WHERE apify_run_id=%s AND ingestion_status NOT IN ('processing','completed') RETURNING id",(run_id,)).fetchone()
  return bool(row)
