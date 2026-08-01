import hashlib
from models.products import Product
from services.compatibility import evaluate_product_compatibility
from services.elasticsearch_client import PRODUCTS_INDEX,get_elasticsearch_client,require_write_access
from services.search_profile import build_component_search_profile
def ingest_discovery_candidate(item,project,client=None):
 require_write_access();identity=item.get('candidate_identity',{});name=identity.get('title')
 if not name:raise ValueError('Discovery candidate has no product title.')
 mpn=identity.get('manufacturer_part_number');manufacturer=identity.get('manufacturer') or 'Unknown';model=identity.get('model') or ''
 key=mpn or f'{manufacturer}|{model}' if model else f"{manufacturer}|{name}";product_id='discovered-'+hashlib.sha256(key.lower().encode()).hexdigest()[:24]
 category=item.get('search_profile',{}).get('category') or 'unknown';specs=item.get('candidate_specifications') or {}
 product=Product(product_id=product_id,manufacturer=manufacturer,name=name,model=model,manufacturer_part_number=mpn or '',category=category,description='Candidate discovered from an approved source; specifications require verification.',source_type='apify_discovery',source_url=item.get('source_url',''),specification_confidence=item.get('extraction',{}).get('confidence',0),**{k:v for k,v in specs.items() if k in Product.model_fields})
 role_id=item.get('component_role_id');profile=build_component_search_profile(project,role_id);evaluation=evaluate_product_compatibility(profile,product)
 source=product.model_dump(mode='json');source['semantic_text']=product.semantic_content();(client or get_elasticsearch_client()).index(index=PRODUCTS_INDEX,id=product.product_id,document=source)
 return product,evaluation
