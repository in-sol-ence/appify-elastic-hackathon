from services.apify_client import ApifyService
class Actor:
 def start(self,**kwargs):return {'id':'run'}
class Dataset:
 def list_items(self,**kwargs):return type('Page',(),{'items':[{'x':1}]})()
class Client:
 def actor(self,id):return Actor()
 def dataset(self,id):return Dataset()
def test_start_and_dataset_with_mocked_apify():
 service=ApifyService(Client());assert service.start_actor({},'actor')['id']=='run';assert service.get_dataset_items('d')==[{'x':1}]
