#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from services.apify_client import test_apify_connection
try:
 result=test_apify_connection();print(f"Authentication success: {'yes' if result['authenticated'] else 'no'}");print(f"Account ID: {result['user_id'] or 'not available'}");print(f"Configured Actor exists: {'yes' if result['actor_exists'] else 'no'}");print(f"Datasets accessible: {'yes' if result['datasets_accessible'] else 'no'}")
except Exception as error:print(f"Apify connection test failed: {error}",file=sys.stderr);raise SystemExit(1)
