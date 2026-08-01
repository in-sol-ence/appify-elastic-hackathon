from models.monitoring import ComponentProcurementState,MonitoringPreference,MonitoredProductSource
from models.urgency import ComponentUrgency
from services.monitoring_scheduler import reconcile_source_schedule,select_monitoring_schedule

def u(score,level):return ComponentUrgency(score=score,level=level)
def test_tiers_and_override_and_received_reduction():
 assert select_monitoring_schedule(u(85,'Critical'),ComponentProcurementState()).frequency_hours==1
 pref=MonitoringPreference(id='i',project_id='p',component_role_id='r',user_override_frequency_hours=7)
 assert select_monitoring_schedule(u(65,'High'),ComponentProcurementState(),pref).frequency_hours==7
 result=select_monitoring_schedule(u(90,'Critical'),ComponentProcurementState(purchase_status='Received',verification_status='Integrated'));assert result.tier=='Minimal' and result.frequency_hours>=168
def test_schedule_unchanged_or_created():
 stable=select_monitoring_schedule(u(65,'High'),ComponentProcurementState(),current_tier='High');assert not stable.changed
 class Service:
  def create_schedule(self,*args):return {'id':'schedule'}
 class Repo:
  def __init__(self):self.saved=None
  def set_schedule(self,*args):self.saved=args
 source=MonitoredProductSource(id='s',project_id='p',component_role_id='r',product_id='x',source_url='https://example.com',monitoring_tier='Low')
 repo=Repo();decision=select_monitoring_schedule(u(65,'High'),ComponentProcurementState(),current_tier='Low');assert reconcile_source_schedule(source,decision,'actor',None,repo,Service())=='schedule' and repo.saved
