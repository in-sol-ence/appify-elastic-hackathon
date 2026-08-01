---
name: apify-elasticsearch-pipeline
description: Transfers cleaned Apify dataset items into an Elasticsearch index with batching and optional stable document IDs. Use when implementing or running the hackathon ingestion pipeline from Apify to Elasticsearch.
compatibility: Requires Node.js 22+, APIFY_TOKEN, ES_URL, Elasticsearch credentials, and ES_ALLOW_WRITES=1.
---

# Apify to Elasticsearch

This project-local helper streams a dataset in pages and sends Elasticsearch bulk requests in batches. It does not install dependencies or store credentials globally.

## Before ingestion

1. Load `.env`: `set -a; source .env; set +a`.
2. Inspect representative Apify items and define the Elasticsearch mapping first when practical.
3. Use a dedicated hackathon index or alias, not an unrelated existing index.
4. Set `ES_ALLOW_WRITES=1` only for the ingestion command.

## Run

```bash
ES_ALLOW_WRITES=1 node .pi/skills/apify-elasticsearch-pipeline/scripts/ingest.mjs DATASET_ID INDEX [ID_FIELD]
```

- `ID_FIELD` is optional. When present, its scalar value becomes Elasticsearch `_id`, making reruns idempotent for those records.
- Without `ID_FIELD`, Elasticsearch assigns IDs and reruns can duplicate documents.
- Default page/batch size is 500; override with `PIPELINE_BATCH_SIZE` (1–1000).
- The helper stops on any bulk item error and reports a compact sample. It never deletes source or destination data.

After ingestion, unset write access and verify with the guarded Elasticsearch helper:

```bash
ES_ALLOW_WRITES=0 node .pi/skills/elasticsearch/scripts/es.mjs request GET /INDEX/_count
```
