from models.monitoring import ComponentProcurementState,MonitoringPreference,MonitoredProductSource
from models.urgency import ComponentUrgency,MonitoringScheduleDecision
TIERS={'Critical':1,'High':4,'Medium':12,'Low':24,'Minimal':120};ORDER=['Minimal','Low','Medium','High','Critical']
def select_monitoring_schedule(urgency:ComponentUrgency,state:ComponentProcurementState,preference:MonitoringPreference|None=None,consecutive_failures:int=0,current_tier:str|None=None)->MonitoringScheduleDecision:
 tier=urgency.level;hours=TIERS[tier];reason=f"Urgency {urgency.score:.1f} selects {tier}."
 if preference and preference.user_override_frequency_hours:hours=preference.user_override_frequency_hours;reason='User frequency override applied.'
 if state.purchase_status=='Received' and state.verification_status in {'Specification reviewed','Bench tested','Integrated'}:tier='Minimal';hours=max(hours,168);reason='Received and verified; commercial monitoring reduced.'
 if consecutive_failures>=3:hours=max(hours,24);reason+=' Repeated source failures reduce request frequency.'
 if preference and preference.minimum_monitoring_tier and ORDER.index(tier)<ORDER.index(preference.minimum_monitoring_tier):tier=preference.minimum_monitoring_tier;hours=min(hours,TIERS[tier])
 if preference and preference.maximum_monitoring_tier and ORDER.index(tier)>ORDER.index(preference.maximum_monitoring_tier):tier=preference.maximum_monitoring_tier;hours=max(hours,TIERS[tier])
 return MonitoringScheduleDecision(tier=tier,frequency_hours=hours,reason=reason,changed=tier!=current_tier)
def cron_for_hours(hours:int)->str:
 if hours==1:return '0 * * * *'
 if hours<24:return f'0 */{hours} * * *'
 if hours<=48:return '0 6 * * *'
 return '0 6 */5 * *'
def reconcile_source_schedule(source:MonitoredProductSource,decision:MonitoringScheduleDecision,actor_id:str,task_id:str|None,repository,apify_service):
 if not decision.changed:return source.apify_schedule_id
 action={'type':'RUN_ACTOR_TASK' if task_id else 'RUN_ACTOR','actorTaskId':task_id,'actorId':None if task_id else actor_id}
 if source.apify_schedule_id:result=apify_service.update_schedule(source.apify_schedule_id,cron_for_hours(decision.frequency_hours),[action])
 else:result=apify_service.create_schedule(f"rbg-{source.id}",cron_for_hours(decision.frequency_hours),[action])
 repository.set_schedule(source.id,decision.tier,result['id']);return result['id']
