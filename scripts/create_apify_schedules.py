#!/usr/bin/env python3
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from services.apify_client import ApifyService
parser=argparse.ArgumentParser();parser.add_argument('config',help='Reviewed JSON schedule configuration');args=parser.parse_args()
try:
 data=json.loads(Path(args.config).read_text());result=ApifyService().create_schedule(data['name'],data['cron_expression'],data['actions']);print(f"Created Apify Schedule: {result.get('id')}")
except Exception as error:print(f"Schedule creation failed: {error}",file=sys.stderr);raise SystemExit(1)
