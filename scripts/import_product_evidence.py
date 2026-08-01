#!/usr/bin/env python3
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from elasticsearch.helpers import bulk
from models.products import ProductEvidence
from services.elasticsearch_client import EVIDENCE_INDEX,get_elasticsearch_client,require_write_access
parser=argparse.ArgumentParser();parser.add_argument('paths',nargs='*',default=['data/evidence/development_evidence.json']);args=parser.parse_args()
try:require_write_access()
except Exception as error:print(error,file=sys.stderr);raise SystemExit(1)
actions=[];invalid=[]
for filename in args.paths:
 try:data=json.loads(Path(filename).read_text())
 except Exception as error:print(f"Cannot read {filename}: {error}",file=sys.stderr);raise SystemExit(1)
 for index,row in enumerate(data):
  try:
   evidence=ProductEvidence.model_validate(row);source=evidence.model_dump(mode='json');source['semantic_text']=evidence.semantic_text or f"{evidence.title}. {evidence.text}";actions.append({'_index':EVIDENCE_INDEX,'_id':evidence.evidence_id,'_source':source})
  except Exception as error:invalid.append(f"{filename} row {index+1}: {error}")
try:
 client=get_elasticsearch_client();success,errors=bulk(client,actions,raise_on_error=False)
 if errors:
  lexical=[]
  for action in actions:
   source=dict(action['_source']);source.pop('semantic_text',None);lexical.append({**action,'_source':source})
  success,errors=bulk(client,lexical,raise_on_error=False)
  if not errors:print("Semantic indexing was unavailable; evidence imported with lexical fields only.")
 print(f"Evidence indexed: {success}; rejected: {len(errors)}; invalid: {len(invalid)}")
 for item in invalid[:10]:print(item,file=sys.stderr)
except Exception as error:print(f"Evidence import failed: {error}",file=sys.stderr);raise SystemExit(1)
