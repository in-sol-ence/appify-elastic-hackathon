from models.urgency import ComponentUrgency
from services.procurement_recommendation import recommend_procurement

def u(level,score):return ComponentUrgency(level=level,score=score)
def action(*args,**kwargs):return recommend_procurement(*args,**kwargs).action
def test_order_monitor_alternative_wait_defer_and_stale():
 assert action(u('Critical',90),'Compatible','in_stock','Safe')=='order_now'
 assert action(u('Low',25),'Compatible','in_stock','Safe')=='continue_monitoring'
 assert action(u('High',70),'Compatible','backorder','Late',alternatives=2)=='select_alternative'
 assert action(u('Low',15),'Compatible','in_stock','Safe',price_position='high',alternatives=3)=='wait_for_better_price'
 assert action(u('Low',15),'Compatible','unknown','Unknown',optional=True)=='defer_optional_component'
 assert action(u('High',70),'Compatible','in_stock','Safe',freshness='stale')=='refresh_stale_data'
def test_compatibility_is_hard_gate():assert action(u('Critical',95),'Incompatible','in_stock','Safe')=='select_alternative'
