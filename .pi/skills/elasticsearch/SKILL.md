---
name: elasticsearch
description: Queries and manages Elasticsearch through a guarded project-local REST helper. Use for mappings, search, indexing, bulk ingestion, and cluster checks in this hackathon project.
compatibility: Requires Node.js 22+ and ES_URL plus credentials in the project environment.
---

# Elasticsearch

Keep connection details in the project root `.env` (gitignored), never in Pi settings or command arguments.

## Setup

```bash
set -a; source .env; set +a
```

Authentication supports `ES_API_KEY`, or `ES_USERNAME` plus `ES_PASSWORD`.

## Commands

Run from the repository root:

```bash
node .pi/skills/elasticsearch/scripts/es.mjs health
node .pi/skills/elasticsearch/scripts/es.mjs search INDEX query.json
node .pi/skills/elasticsearch/scripts/es.mjs request GET /INDEX/_mapping
node .pi/skills/elasticsearch/scripts/es.mjs request PUT /INDEX mapping.json
```

`query.json` and request bodies must be workspace-relative JSON files. The helper blocks mutation by default. Set `ES_ALLOW_WRITES=1` only for an intentional indexing or administration command, then unset it. Never enable writes merely to troubleshoot a read.

Before changing mappings or deleting anything, inspect the target index and explain the intended effect. Never disable TLS verification. Avoid destructive APIs during the hackathon unless the user explicitly requests them.
