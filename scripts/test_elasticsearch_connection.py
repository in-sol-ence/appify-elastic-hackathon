#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from services.elasticsearch_client import test_connection

try:
    result=test_connection();print("Elasticsearch reachable: yes");print(f"Cluster: {result['cluster_name']}");print(f"Version: {result['version']}")
    for name,exists in result["indices"].items():print(f"Index {name}: {'exists' if exists else 'missing'}")
except Exception as error:
    print(f"Elasticsearch connection test failed: {error}",file=sys.stderr);raise SystemExit(1)
