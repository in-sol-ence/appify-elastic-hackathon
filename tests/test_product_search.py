from elastic_transport import ApiResponseMeta,NodeConfig
from elasticsearch import BadRequestError
from models.products import Product
from services.elasticsearch_client import ProductSearchUnavailable
from services.product_search import build_product_query,hard_filters,search_products
from services.search_profile import build_component_search_profile
from services.templates import build_sample_project

class Client:
 def __init__(self,responses):self.responses=list(responses);self.calls=[]
 def search(self,**kwargs):self.calls.append(kwargs);response=self.responses.pop(0);return response() if callable(response) else response

def setup_profile():
 project=build_sample_project();role=next(r for r in project.component_roles if r.role_name=="Motor driver");role.acceptance_requirements={"voltage":"24 V","current":"15 A","interface":"PWM or UART"};return build_component_search_profile(project,role.id)
def hit():
 p=Product(product_id="dev",manufacturer="Dev",name="Driver",category="motor_driver",input_voltage_min_v=12,input_voltage_max_v=30,continuous_current_per_channel_a=20,control_interfaces=["PWM"]);return {"hits":{"hits":[{"_score":3,"_source":p.model_dump(mode="json")|{"semantic_text":p.semantic_content()}}]}}
def bad_request():
 meta=ApiResponseMeta(400,"1.1",{},0,NodeConfig("http","localhost",9200));raise BadRequestError("semantic unavailable",meta,{})
def test_query_has_exact_numeric_and_multiple_interface_filters():
 filters=hard_filters(setup_profile());text=str(filters);assert "category" in text and "input_voltage_min_v" in text and "continuous_current" in text and "PWM" in text and "UART" in text
def test_natural_language_query_and_no_results():
 profile=setup_profile();assert profile.natural_language_description in str(build_product_query(profile));assert search_products(profile,client=Client([{"hits":{"hits":[]}}]))==[]
def test_semantic_failure_uses_lexical_fallback():
 results=search_products(setup_profile(),client=Client([bad_request,hit()]));assert results and "Keyword search" in results[0].search_explanation

def test_elasticsearch_unavailable_is_wrapped():
 class Broken:
  def search(self,**kwargs):raise OSError("offline")
 import pytest
 with pytest.raises(ProductSearchUnavailable):search_products(setup_profile(),client=Broken())
