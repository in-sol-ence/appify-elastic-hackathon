from datetime import datetime,timezone,timedelta
from models.observations import ProductObservation,ExtractionResult,ExtractionStatus
from services.product_change_detection import detect_changes,observation_id

def obs(price=100,availability='in_stock',delivery=5,status='success',hash='a',error=None):
 now=datetime.now(timezone.utc);return ProductObservation(monitoring_job_id='j',project_id='p',component_role_id='r',product_id='x',source_id='s',actor_run_id='run',observed_at=now,source_type='supplier_product_page',source_url='https://example.com',commercial={'price':price,'availability':availability,'delivery_latest':now+timedelta(days=delivery)},evidence={'content_hash':hash},extraction=ExtractionResult(status=status,confidence=.9,error_category=error))
def kinds(previous,current,**kwargs):return {e.event_type for e in detect_changes(previous,current,**kwargs)}
def test_price_stock_shipping_and_unknown_rules():
 old=obs();new=obs(110,'out_of_stock',10,hash='b');types=kinds(old,new);assert {'price_increased','became_unavailable','delivery_delayed','content_changed'}<=types
 assert 'price_decreased' in kinds(old,obs(80))
 assert not any('available' in x for x in kinds(old,obs(100,'unknown')))
def test_failure_recovery_and_repeated_missing():
 old=obs(status='failed',error='HTTPStatusError');new=obs();assert 'source_recovered' in kinds(old,new)
 failed=obs(status='failed',error='listing_missing');assert {'source_extraction_failed','listing_removed'}<=kinds(new,failed,repeated_missing_count=2)
def test_observation_identity_is_stable():
 item=obs();assert observation_id(item)==observation_id(item)
