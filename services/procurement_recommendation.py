from datetime import datetime,timezone,timedelta
from models.recommendations import ProcurementRecommendation
from models.urgency import ComponentUrgency

def recommend_procurement(urgency:ComponentUrgency,compatibility:str,availability:str,delivery_fit:str,price_position:str='normal',alternatives:int=0,purchase_status:str='Not planned',verification_status:str='Unverified',freshness:str='fresh',optional:bool=False,previous_action=None)->ProcurementRecommendation:
 facts=[f"Urgency is {urgency.level} ({urgency.score:.1f}).",f"Availability is {availability}.",f"Delivery fit is {delivery_fit}.",f"Compatibility is {compatibility}."]
 uncertainty=[]
 if freshness!='fresh':action='refresh_stale_data';reason='Refresh required before making a purchasing decision.';uncertainty.append('Availability or delivery data is stale.')
 elif compatibility=='Incompatible':action='select_alternative';reason='The selected product fails a hard compatibility requirement.'
 elif compatibility in {'Potentially compatible','Insufficient information'}:action='verify_compatibility';reason='Compatibility has unresolved technical requirements.'
 elif purchase_status in {'Ordered','Received'}:action='no_action';reason=f"Product is already {purchase_status.lower()}."
 elif optional and urgency.level in {'Minimal','Low'}:action='defer_optional_component';reason='The optional component is not urgent.'
 elif urgency.level in {'Critical','High'} and availability in {'in_stock','limited_stock'} and delivery_fit in {'Safe','Tight'}:action='order_now';reason='Waiting creates schedule risk while a compatible product can arrive in time.'
 elif availability in {'out_of_stock','backorder','discontinued'} and alternatives>0:action='select_alternative';reason='The current product cannot meet procurement needs and alternatives exist.'
 elif urgency.level in {'Minimal','Low'} and price_position=='high' and alternatives>1:action='wait_for_better_price';reason='Price is above recent history and the schedule permits waiting.'
 elif urgency.level in {'Medium','High'}:action='order_soon';reason='Procurement should begin soon to preserve schedule margin.'
 else:action='continue_monitoring';reason='Current risk does not justify immediate purchase.'
 changed=[]
 if previous_action and previous_action!=action:changed=[f"Recommendation changed from {previous_action} to {action}.",*facts]
 return ProcurementRecommendation(action=action,priority=urgency.level,reason=reason,supporting_facts=facts,confidence=.9 if freshness=='fresh' and compatibility=='Compatible' else .6,expires_at=datetime.now(timezone.utc)+timedelta(hours=2 if urgency.level=='Critical' else 24),remaining_uncertainty=uncertainty,previous_action=previous_action,change_explanation=changed)
