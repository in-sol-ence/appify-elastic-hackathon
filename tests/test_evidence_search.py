from services.product_evidence_search import search_product_evidence

class Client:
 def search(self,**kwargs):return {"hits":{"hits":[{"_source":{"evidence_id":"e","product_id":"p","source_type":"Datasheet","title":"PWM support","text":"Supports PWM control","source_authority":.9}}]}}
def test_evidence_search_returns_validated_chunks():
 results=search_product_evidence("p","PWM",client=Client());assert results[0].title=="PWM support" and results[0].source_authority==.9
