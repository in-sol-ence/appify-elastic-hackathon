import re
from models.observations import ProductObservation
def normalize(value):return re.sub(r'[^a-z0-9]+','',value.lower()) if value else ''
def verify_product_identity(observation:ProductObservation,expected:dict,supplier_sku_map:dict|None=None)->tuple[bool,str]:
 actual=observation.identity;expected_mpn=expected.get('manufacturer_part_number')
 if expected_mpn and actual.manufacturer_part_number:return (normalize(expected_mpn)==normalize(actual.manufacturer_part_number),'manufacturer_part_number')
 if expected.get('manufacturer') and expected.get('model') and actual.manufacturer and actual.model:return (normalize(expected['manufacturer'])==normalize(actual.manufacturer) and normalize(expected['model'])==normalize(actual.model),'manufacturer_and_model')
 if actual.supplier_sku and supplier_sku_map and actual.supplier_sku in supplier_sku_map:return (supplier_sku_map[actual.supplier_sku]==observation.product_id,'supplier_sku')
 if expected.get('title') and actual.title:return (normalize(expected['title'])==normalize(actual.title),'normalized_exact_title')
 return False,'insufficient_identity'
