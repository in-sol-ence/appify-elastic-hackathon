from services.apify_client import ApifyService
class Actor:
 def start(self,**kwargs):return {'id':'run'}
 def call(self,**kwargs):return {'id':'analysis-run','status':'SUCCEEDED','defaultDatasetId':'d'}
class Dataset:
 def list_items(self,**kwargs):return type('Page',(),{'items':[{'x':1}]})()
class Client:
 def actor(self,id):return Actor()
 def dataset(self,id):return Dataset()
def test_start_and_dataset_with_mocked_apify():
 service=ApifyService(Client());assert service.start_actor({},'actor')['id']=='run';assert service.get_dataset_items('d')==[{'x':1}]
 run,items=service.call_actor_and_get_items('actor',{});assert run['id']=='analysis-run' and items==[{'x':1}]
