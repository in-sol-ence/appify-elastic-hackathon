from uuid import UUID,uuid4
import psycopg
from models.monitoring import MonitoredProductSource,MonitoringPreference
from repositories.database import get_connection
from repositories.exceptions import DatabaseConnectionError,RepositoryError
class MonitoringRepository:
 def __init__(self,database_url=None):self.database_url=database_url
 def create_source(self,project_id,component_role_id,product_id,source_url,supplier_name=None,source_type='supplier_product_page',tier='Low',actor_id=None,task_id=None):
  sid=uuid4()
  try:
   with get_connection(self.database_url) as c:
    row=c.execute('''INSERT INTO monitored_product_sources(id,project_id,component_role_id,product_id,source_type,source_url,supplier_name,apify_actor_id,apify_task_id,monitoring_tier) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(project_id,component_role_id,product_id,source_url) DO UPDATE SET supplier_name=EXCLUDED.supplier_name,updated_at=CURRENT_TIMESTAMP RETURNING *''',(sid,UUID(project_id),UUID(component_role_id),product_id,source_type,source_url,supplier_name,actor_id,task_id,tier)).fetchone()
   return MonitoredProductSource.model_validate({**row,'id':str(row['id']),'project_id':str(row['project_id']),'component_role_id':str(row['component_role_id'])})
  except (DatabaseConnectionError,psycopg.Error) as error:raise RepositoryError('Monitoring source could not be saved.') from error
 def list_sources(self,project_id,component_role_id=None):
  sql='SELECT * FROM monitored_product_sources WHERE project_id=%s';params=[UUID(project_id)]
  if component_role_id:sql+=' AND component_role_id=%s';params.append(UUID(component_role_id))
  sql+=' ORDER BY updated_at DESC'
  try:
   with get_connection(self.database_url) as c:rows=c.execute(sql,params).fetchall()
   return [MonitoredProductSource.model_validate({**r,'id':str(r['id']),'project_id':str(r['project_id']),'component_role_id':str(r['component_role_id'])}) for r in rows]
  except (DatabaseConnectionError,psycopg.Error) as error:raise RepositoryError('Monitoring sources could not be loaded.') from error
 def get_source(self,source_id):
  with get_connection(self.database_url) as c:row=c.execute('SELECT * FROM monitored_product_sources WHERE id=%s',(UUID(source_id),)).fetchone()
  return MonitoredProductSource.model_validate({**row,'id':str(row['id']),'project_id':str(row['project_id']),'component_role_id':str(row['component_role_id'])}) if row else None
 def set_enabled(self,source_id,enabled):
  with get_connection(self.database_url) as c:c.execute('UPDATE monitored_product_sources SET monitoring_enabled=%s,updated_at=CURRENT_TIMESTAMP WHERE id=%s',(enabled,UUID(source_id)))
 def set_schedule(self,source_id,tier,schedule_id):
  with get_connection(self.database_url) as c:c.execute('UPDATE monitored_product_sources SET monitoring_tier=%s,apify_schedule_id=%s,updated_at=CURRENT_TIMESTAMP WHERE id=%s',(tier,schedule_id,UUID(source_id)))
 def mark_success(self,source_id,observed_at):
  with get_connection(self.database_url) as c:c.execute('UPDATE monitored_product_sources SET last_successful_run_at=CURRENT_TIMESTAMP,last_observation_at=%s,consecutive_failures=0,updated_at=CURRENT_TIMESTAMP WHERE id=%s',(observed_at,UUID(source_id)))
 def mark_failure(self,source_id):
  with get_connection(self.database_url) as c:c.execute('UPDATE monitored_product_sources SET last_failed_run_at=CURRENT_TIMESTAMP,consecutive_failures=consecutive_failures+1,updated_at=CURRENT_TIMESTAMP WHERE id=%s',(UUID(source_id),))
 def get_preference(self,project_id,role_id):
  with get_connection(self.database_url) as c:row=c.execute('SELECT * FROM product_monitoring_preferences WHERE project_id=%s AND component_role_id=%s',(UUID(project_id),UUID(role_id))).fetchone()
  return MonitoringPreference.model_validate({**row,'id':str(row['id']),'project_id':str(row['project_id']),'component_role_id':str(row['component_role_id'])}) if row else None
 def save_preference(self,preference):
  p=preference
  with get_connection(self.database_url) as c:c.execute('''INSERT INTO product_monitoring_preferences(id,project_id,component_role_id,enabled,minimum_monitoring_tier,maximum_monitoring_tier,user_override_frequency_hours,monitor_price,monitor_availability,monitor_shipping,monitor_product_changes) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(project_id,component_role_id) DO UPDATE SET enabled=EXCLUDED.enabled,minimum_monitoring_tier=EXCLUDED.minimum_monitoring_tier,maximum_monitoring_tier=EXCLUDED.maximum_monitoring_tier,user_override_frequency_hours=EXCLUDED.user_override_frequency_hours,monitor_price=EXCLUDED.monitor_price,monitor_availability=EXCLUDED.monitor_availability,monitor_shipping=EXCLUDED.monitor_shipping,monitor_product_changes=EXCLUDED.monitor_product_changes,updated_at=CURRENT_TIMESTAMP''',(UUID(p.id),UUID(p.project_id),UUID(p.component_role_id),p.enabled,p.minimum_monitoring_tier,p.maximum_monitoring_tier,p.user_override_frequency_hours,p.monitor_price,p.monitor_availability,p.monitor_shipping,p.monitor_product_changes))
