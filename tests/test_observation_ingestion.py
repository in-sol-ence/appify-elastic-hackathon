from datetime import datetime,timezone
from elastic_transport import ApiResponseMeta,NodeConfig
from elasticsearch import ConflictError,NotFoundError
import services.observation_ingestion as ingestion
from models.observations import ProductObservation,ExtractionResult

def error(cls):return cls('error',ApiResponseMeta(404,'1.1',{},0,NodeConfig('http','localhost',9200)),{})
class Client:
 def __init__(self,duplicate=False):self.duplicate=duplicate;self.created=[];self.indexed=[]
 def create(self,**kwargs):
  if self.duplicate:raise error(ConflictError)
  self.created.append(kwargs)
 def index(self,**kwargs):self.indexed.append(kwargs)
 def get(self,**kwargs):raise error(NotFoundError)
def observation():return ProductObservation(monitoring_job_id='j',project_id='p',component_role_id='r',product_id='x',source_id='s',actor_run_id='a',observed_at=datetime.now(timezone.utc),source_type='supplier_product_page',source_url='https://example.com',identity={'manufacturer_part_number':'ABC'},commercial={'price':10,'availability':'in_stock'},extraction=ExtractionResult(status='success',confidence=.9))
def test_valid_observation_indexes_history_and_current(monkeypatch):
 monkeypatch.setenv('ES_ALLOW_WRITES','1');monkeypatch.setattr(ingestion,'_previous',lambda *args:None);client=Client();result=ingestion.ingest_observation(observation(),{'manufacturer_part_number':'ABC'},client=client)
 assert not result['duplicate'] and client.created and any('current' in item['index'] for item in client.indexed)
def test_duplicate_observation_is_idempotent(monkeypatch):
 monkeypatch.setenv('ES_ALLOW_WRITES','1');assert ingestion.ingest_observation(observation(),{'manufacturer_part_number':'ABC'},client=Client(True))['duplicate']
