from datetime import datetime,timezone
from models.observations import ProductObservation,ExtractionResult
from services.product_identity import verify_product_identity
def item(identity):return ProductObservation(monitoring_job_id='j',project_id='p',component_role_id='r',product_id='x',source_id='s',actor_run_id='a',observed_at=datetime.now(timezone.utc),source_type='supplier_product_page',source_url='https://example.com',identity=identity,extraction=ExtractionResult(status='success',confidence=1))
def test_identity_order_and_mismatch():
 assert verify_product_identity(item({'manufacturer_part_number':'ABC-123'}),{'manufacturer_part_number':'abc123'})[0]
 assert verify_product_identity(item({'manufacturer':'Maker','model':'M1'}),{'manufacturer':'Maker','model':'M1'})[0]
 assert not verify_product_identity(item({'title':'Different'}),{'title':'Expected'})[0]
