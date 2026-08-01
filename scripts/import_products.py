#!/usr/bin/env python3
import argparse,csv,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from elasticsearch.helpers import bulk
from models.products import Product
from services.elasticsearch_client import PRODUCTS_INDEX,get_elasticsearch_client,require_write_access

def stable_id(row):
 if row.get("manufacturer_part_number"):key=f"mpn|{row['manufacturer_part_number']}"
 elif row.get("manufacturer") and row.get("model"):key=f"model|{row['manufacturer']}|{row['model']}"
 elif row.get("product_id"):return str(row["product_id"])
 else:key=json.dumps(row,sort_keys=True,default=str)
 return "product-"+hashlib.sha256(key.strip().lower().encode()).hexdigest()[:24]
def rows(path):
 if path.suffix.lower()=='.json':
  data=json.loads(path.read_text());return data if isinstance(data,list) else data.get('products',[])
 with path.open(newline='') as f:return list(csv.DictReader(f))
def normalize(row):
 row=dict(row)
 for field in ['intended_applications','important_features','motor_types','control_interfaces','communication_interfaces','supported_operating_systems','supported_software']:
  if isinstance(row.get(field),str):row[field]=[item.strip() for item in row[field].replace(';',',').split(',') if item.strip()]
 for source,target,scale in [('input_voltage_min_mv','input_voltage_min_v',.001),('input_voltage_max_mv','input_voltage_max_v',.001),('weight_kg','weight_g',1000)]:
  if source in row and row[source] not in ('',None):row[target]=float(row.pop(source))*scale
 return row
def main():
 parser=argparse.ArgumentParser();parser.add_argument('paths',nargs='*',default=['data/products/source_backed_catalog.json']);args=parser.parse_args()
 require_write_access();client=get_elasticsearch_client();actions=[];invalid=[]
 for filename in args.paths:
  for index,row in enumerate(rows(Path(filename))):
   try:
    row=normalize({k:v for k,v in row.items() if v not in ('',None)});row['product_id']=stable_id(row);product=Product.model_validate(row);source=product.model_dump(mode='json');source['semantic_text']=product.semantic_content();actions.append({'_index':PRODUCTS_INDEX,'_id':product.product_id,'_source':source})
   except Exception as error:invalid.append(f"{filename} row {index+1}: {error}")
 existing=set()
 if actions:
  response=client.mget(index=PRODUCTS_INDEX,ids=[a['_id'] for a in actions],_source=False);existing={doc['_id'] for doc in response.get('docs',[]) if doc.get('found')}
 success,errors=bulk(client,actions,raise_on_error=False)
 if errors:
  lexical_actions=[]
  for action in actions:
   source=dict(action['_source']);source.pop('semantic_text',None);lexical_actions.append({**action,'_source':source})
  success,errors=bulk(client,lexical_actions,raise_on_error=False)
  if not errors:print("Semantic indexing was unavailable; products imported with lexical fields only.")
 print(f"Inserted: {sum(a['_id'] not in existing for a in actions)}")
 print(f"Updated: {sum(a['_id'] in existing for a in actions)}")
 print(f"Rejected by Elasticsearch: {len(errors)}");print(f"Invalid records: {len(invalid)}")
 for error in invalid[:10]:print(error,file=sys.stderr)
 return 0 if not errors else 1
if __name__=='__main__':
 try:raise SystemExit(main())
 except Exception as error:print(f"Product import failed: {error}",file=sys.stderr);raise SystemExit(1)
