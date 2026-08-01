#!/usr/bin/env python3
import copy,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from services.elasticsearch_client import get_elasticsearch_client,require_write_access
from services.elasticsearch_indices import INDEX_MAPPINGS

try:
    require_write_access();client=get_elasticsearch_client();created=[]
    for name,mapping in INDEX_MAPPINGS.items():
        if not client.indices.exists(index=name):
            try:client.indices.create(index=name,**mapping)
            except Exception:
                fallback=copy.deepcopy(mapping)
                if "semantic_text" not in fallback["mappings"]["properties"]:raise
                fallback["mappings"]["properties"]["semantic_text"]={"type":"text"}
                client.indices.create(index=name,**fallback)
                print(f"{name}: semantic_text unavailable; initialized with lexical text fallback.")
            created.append(name)
    print("Elasticsearch indices ready." + (f" Created: {', '.join(created)}" if created else " No changes required."))
except Exception as error:
    print(f"Elasticsearch initialization failed: {error}",file=sys.stderr);raise SystemExit(1)
