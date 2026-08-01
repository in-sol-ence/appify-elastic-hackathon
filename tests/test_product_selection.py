from models.enums import SelectionStatus
from models.products import Product
from services.product_selection import apply_catalog_product,reject_catalog_product
from services.templates import build_sample_project


def catalog(pid,name):return Product(product_id=pid,manufacturer="Dev",name=name,model=name,manufacturer_part_number=pid,category="onboard_computer",price_estimate=50,input_voltage_min_v=5,input_voltage_max_v=12)
def test_candidate_primary_replacement_and_snapshot():
 project=build_sample_project();role=project.component_roles[0]
 first,_=apply_catalog_product(project,role.id,catalog("a","A"),True);second,report=apply_catalog_product(project,role.id,catalog("b","B"),True)
 assert not first.primary_product and second.primary_product and second.elastic_product_id=="b" and second.catalog_specs["input_voltage_min_v"]==5
 assert role.id in report.component_roles

def test_rejection_is_preserved():
 project=build_sample_project();role=project.component_roles[0];item=reject_catalog_product(project,role.id,catalog("x","X"),"Too expensive")
 assert item.selection_status==SelectionStatus.REJECTED and item.rejection_reason=="Too expensive" and item.rejected_at
