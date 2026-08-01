from datetime import datetime,timezone,timedelta
STALE_HOURS={'Critical':2,'High':8,'Medium':24,'Low':48,'Minimal':192}
def freshness(last_observation,tier,now=None):
 if not last_observation:return 'missing'
 now=now or datetime.now(timezone.utc);age=(now-last_observation).total_seconds()/3600
 return 'fresh' if age<=STALE_HOURS.get(tier,48) else 'stale'
def availability_score(state,active_sources=1,confidence=1,fresh=True):
 base={'in_stock':100 if active_sources>1 else 80,'limited_stock':60,'preorder':35,'backorder':20,'out_of_stock':0,'discontinued':0,'unknown':30}.get(state,30)
 return round(base*max(.2,min(1,confidence))*(1 if fresh else .6),1)
def delivery_fit(required_by,delivery_latest,integration_risk,buffer_days=None):
 if not required_by or not delivery_latest:return 'Unknown',None
 buffer=buffer_days if buffer_days is not None else {1:2,2:4,3:7,4:14,5:21}[integration_risk]
 margin=(required_by-delivery_latest.date()).days-buffer
 return ('Safe' if margin>=7 else 'Tight' if margin>=0 else 'Late'),margin
