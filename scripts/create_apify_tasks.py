#!/usr/bin/env python3
import argparse,json,os,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from services.apify_client import ApifyService
parser=argparse.ArgumentParser();parser.add_argument('config',help='Reviewed JSON task configuration');args=parser.parse_args()
try:
 data=json.loads(Path(args.config).read_text());actor=data.get('actor_id') or os.getenv('APIFY_PRODUCT_MONITOR_ACTOR_ID');result=ApifyService().create_task(data['name'],actor,data['task_input']);print(f"Created Apify Task: {result.get('id')}")
except Exception as error:print(f"Task creation failed: {error}",file=sys.stderr);raise SystemExit(1)
