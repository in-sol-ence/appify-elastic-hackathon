#!/usr/bin/env python3
import argparse,os,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from services.elasticsearch_client import get_elasticsearch_client,require_write_access
from services.elasticsearch_indices import INDEX_MAPPINGS
parser=argparse.ArgumentParser();parser.add_argument("--confirm-reset",action="store_true");args=parser.parse_args()
if not args.confirm_reset:print("Refusing reset without --confirm-reset",file=sys.stderr);raise SystemExit(2)
url=os.getenv("ELASTICSEARCH_URL","")
if not any(host in url for host in ["localhost","127.0.0.1","::1"]):print("Reset is restricted to local development Elasticsearch.",file=sys.stderr);raise SystemExit(2)
try:
 require_write_access();client=get_elasticsearch_client()
 for name,mapping in INDEX_MAPPINGS.items():
  if client.indices.exists(index=name):client.indices.delete(index=name)
  client.indices.create(index=name,**mapping)
 print("Development Elasticsearch indices reset.")
except Exception as error:print(f"Reset failed: {error}",file=sys.stderr);raise SystemExit(1)
