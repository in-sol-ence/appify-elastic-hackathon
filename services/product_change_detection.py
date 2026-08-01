import hashlib,json
from models.observations import ProductChangeEvent,ProductObservation,ExtractionStatus,Availability

def observation_id(observation):return hashlib.sha256(f"{observation.actor_run_id}|{observation.source_id}|{observation.observed_at.isoformat()}".encode()).hexdigest()
def _event(current,event_type,previous_value,current_value,magnitude=None):
 key=f"{current.product_id}|{current.source_id}|{event_type}|{current.observed_at.isoformat()}";eid=hashlib.sha256(key.encode()).hexdigest()
 return ProductChangeEvent(event_id=eid,project_id=current.project_id,component_role_id=current.component_role_id,product_id=current.product_id,source_id=current.source_id,event_type=event_type,previous_value=previous_value,current_value=current_value,change_magnitude=magnitude,observed_at=current.observed_at,source_confidence=current.extraction.confidence,supporting_observation_ids=[observation_id(current)])
def detect_changes(previous:ProductObservation|None,current:ProductObservation,price_threshold_percent:float=1.0,repeated_missing_count:int=0)->list[ProductChangeEvent]:
 if current.extraction.status==ExtractionStatus.FAILED:
  events=[_event(current,'source_extraction_failed',previous.extraction.status.value if previous else None,current.extraction.error_category)]
  if repeated_missing_count>=2 and current.extraction.error_category in {'HTTPStatusError','listing_missing'}:events.append(_event(current,'listing_removed',repeated_missing_count,repeated_missing_count+1))
  return events
 if previous is None:return []
 events=[]
 if previous.extraction.status==ExtractionStatus.FAILED:events.append(_event(current,'source_recovered','failed','success'))
 old,new=previous.commercial.price,current.commercial.price
 if old is not None and new is not None and old>0:
  pct=(new-old)/old*100
  if abs(pct)>=price_threshold_percent:events.append(_event(current,'price_increased' if pct>0 else 'price_decreased',old,new,round(pct,2)))
 old_sale=previous.commercial.original_price is not None and previous.commercial.price is not None and previous.commercial.price<previous.commercial.original_price
 new_sale=current.commercial.original_price is not None and current.commercial.price is not None and current.commercial.price<current.commercial.original_price
 if old_sale!=new_sale:events.append(_event(current,'sale_started' if new_sale else 'sale_ended',old_sale,new_sale))
 olda,newa=previous.commercial.availability,current.commercial.availability
 if newa!=Availability.UNKNOWN and olda!=newa:
  if newa==Availability.IN_STOCK:kind='became_available'
  elif newa==Availability.LIMITED_STOCK:kind='limited_stock_detected'
  elif newa==Availability.BACKORDER:kind='backorder_started'
  elif newa in {Availability.OUT_OF_STOCK,Availability.DISCONTINUED}:kind='became_unavailable'
  else:kind=None
  if kind:events.append(_event(current,kind,olda.value,newa.value))
 oldd,newd=previous.commercial.delivery_latest,current.commercial.delivery_latest
 if oldd and newd and oldd!=newd:events.append(_event(current,'delivery_delayed' if newd>oldd else 'delivery_improved',oldd.isoformat(),newd.isoformat(),(newd-oldd).days))
 if previous.product_state.revision!=current.product_state.revision and current.product_state.revision is not None:events.append(_event(current,'product_revision_changed',previous.product_state.revision,current.product_state.revision))
 if previous.product_state.lifecycle_status!=current.product_state.lifecycle_status and current.product_state.lifecycle_status is not None:events.append(_event(current,'lifecycle_status_changed',previous.product_state.lifecycle_status,current.product_state.lifecycle_status))
 if previous.evidence.content_hash and current.evidence.content_hash and previous.evidence.content_hash!=current.evidence.content_hash:events.append(_event(current,'content_changed',previous.evidence.content_hash,current.evidence.content_hash))
 return events
