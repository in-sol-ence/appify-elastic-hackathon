# Robotics BOM Guardian

A Streamlit application for creating, understanding, editing, and deterministically evaluating robotics projects and bills of materials. Projects are validated with Pydantic v2 and persisted as complete JSONB documents in PostgreSQL through Psycopg 3.

This version includes optional Apify-powered product monitoring and Elasticsearch-backed product discovery, evidence, observation history, current listing state, change detection, and source health. PostgreSQL remains authoritative, and no purchasing is automated.

For the complete architecture, data flow, security model, deployment instructions, and troubleshooting guide, see [`docs/APIFY_ELASTICSEARCH_GUIDE.md`](docs/APIFY_ELASTICSEARCH_GUIDE.md).

## Prerequisites

- Python 3.12+
- PostgreSQL 14+ with `psql`
- Permission to create a database and role, or an existing PostgreSQL database

## 1. Create the PostgreSQL role and databases

Run these statements as a PostgreSQL administrator and choose a strong local password:

```sql
CREATE USER bom_app WITH PASSWORD 'replace_with_a_strong_password';
CREATE DATABASE robotics_bom OWNER bom_app;
CREATE DATABASE robotics_bom_test OWNER bom_app;
```

For example:

```bash
psql postgres
```

Then paste the SQL above. The `_test` database is isolated for integration tests and must not contain development data.

## 2. Configure the environment

```bash
cp .env.example .env
```

Set the local connection URL in `.env`:

```env
DATABASE_URL=postgresql://bom_app:your_password@localhost:5432/robotics_bom
```

`.env` is ignored by Git. Credentials are never stored in source code or displayed by the database diagnostic utility.

## 3. Install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

The persistence layer uses `psycopg[binary]` (Psycopg 3) and `python-dotenv`. It does not use psycopg2, SQLAlchemy, or an ORM.

## 4. Initialize the database

Recommended:

```bash
python scripts/init_database.py
```

The utility reads `.env` and executes:

```text
db/migrations/001_create_projects.sql
```

It creates one `projects` table with UUID identity, lifecycle status, JSONB project data, timestamps, and status/update indexes. The migration is idempotent.

You can also use `psql`. Variables in `.env` are not automatically exported to your shell, so either export the URL:

```bash
export DATABASE_URL="postgresql://bom_app:your_password@localhost:5432/robotics_bom"
psql "$DATABASE_URL" -f db/migrations/001_create_projects.sql
```

or pass it directly:

```bash
psql "postgresql://bom_app:your_password@localhost:5432/robotics_bom" \
  -f db/migrations/001_create_projects.sql
```

## 5. Test the connection

```bash
python scripts/test_database_connection.py
```

The command prints only:

- Connected database name
- Current PostgreSQL user
- PostgreSQL version
- Whether `public.projects` exists

It never prints the password or complete connection URL.

## 6. Run the application

```bash
streamlit run app.py
```

Open the URL printed by Streamlit, normally `http://localhost:8501`.

## Application workflow

```text
Home
├── New Project Wizard
└── Project Workspace
    ├── Overview
    ├── Blueprint
    ├── BOM
    └── Settings
```

- **Home** lists PostgreSQL projects and supports open, duplicate, archive, and confirmed delete actions.
- **Overview** explains current milestone readiness, blockers, unresolved decisions, and deterministically ranked next actions.
- **Blueprint** reuses the Graphviz dependency graph with architecture, product, and full-project modes plus filters and component inspection.
- **BOM** combines abstract design roles with manual products, local expected costs, procurement state, filters, CSV export, and JSON export.
- **Component details** open from blockers, Blueprint, or BOM and support role, dependency, status, and manual product management.
- **Settings** edits project information and supports structure editing, duplication, archive, exports, and confirmed deletion.

Readiness and validation remain separate deterministic services. No LLM, external product API, monitoring, supplier scraping, Apify, or Elasticsearch operation is used by this application layer.

## PostgreSQL storage model

Each row contains one complete project aggregate:

```text
projects
├── id             UUID primary key
├── name           searchable display name
├── status         draft | active | archived
├── project_data   complete Pydantic Project as JSONB
├── created_at     PostgreSQL creation timestamp
└── updated_at     PostgreSQL update timestamp
```

Milestones, capabilities, component roles, ratings, relationships, requirement groups, and products remain nested in `project_data`. This preserves the current domain model while leaving room for selective relational normalization or Elasticsearch synchronization later.

The repository boundary is implemented in:

```text
repositories/database.py
repositories/exceptions.py
repositories/project_repository.py
models/persistence.py
```

`ProjectRepository` supports:

- `create_project(project, status)`
- `update_project(project_id, project, status)`
- `get_project(project_id)`
- `list_projects(status)`
- `delete_project(project_id)`
- `project_exists(project_id)`

All SQL values are parameterized. Pydantic serializes with `model_dump(mode="json")`, and loaded JSONB is reconstructed with `Project.model_validate()`.

## Save, load, and delete behavior

- **Save Draft** creates or updates the current row with status `draft`, preserves the current wizard step, and records the database ID and save timestamp in structured session state.
- **Save Project** runs complete domain validation, blocks on blocking findings, and writes status `active`.
- **Load** lists summary columns only, then retrieves complete JSONB for the selected project.
- **Import JSON** accepts a complete Robotics BOM Guardian export, validates all nested data with Pydantic, and loads it as a new unsaved copy with a fresh project UUID.
- **Delete** remains disabled until the user checks the confirmation box.
- Repeated saves update the same UUID row rather than creating duplicates.

The active `WizardState` contains the current project, persisted project ID, current step, validation findings, last save timestamp, persistence status, selected template, and editing state.

To import a project, open **Import an existing project from JSON** on the first wizard step, choose an exported `.json` file, and select **Import JSON project**. Imports are limited to 5 MB and never overwrite an existing PostgreSQL row automatically.

## Test database and test suite

Set a separate test connection. Do not point this variable at `robotics_bom`:

```bash
export TEST_DATABASE_URL="postgresql://bom_app:your_password@localhost:5432/robotics_bom_test"
pytest -q
```

PostgreSQL integration tests refuse to run unless the database name ends in `_test`. They initialize the migration and clean up only records whose names use the test prefix. When `TEST_DATABASE_URL` is absent, integration tests are skipped with a clear reason; model, validation, connection-error, readiness, and UI smoke tests still run.

Repository tests cover creation, JSONB round trips, nested milestones, capabilities, dependencies, products, updates, summary listing, status filtering, deletion, missing records, duplicate UUIDs, and invalid connection URLs.

## Optional migration from the former SQLite repository

SQLite is no longer used by active application paths. Existing `data/robotics_bom_guardian.db` files are not deleted automatically.

After initializing PostgreSQL, migrate compatible old JSON rows with:

```bash
python scripts/migrate_sqlite_projects.py data/robotics_bom_guardian.db
```

The script validates every old JSON document as a current Pydantic `Project`, maps legacy drafts to `draft` and other legacy statuses to `active`, then creates or updates the matching PostgreSQL UUID. Back up the SQLite file before migration.

## Elasticsearch product discovery

PostgreSQL remains authoritative for projects, BOM roles, selected product snapshots, purchase state, and verification state. Elasticsearch is an optional discovery catalog for product search, structured specification filtering, evidence retrieval, similarity, and ranking. The rest of the application continues to work when Elasticsearch is unavailable.

### Configure Elasticsearch

Add either a local node or Elastic Cloud endpoint to `.env`:

```env
ELASTICSEARCH_URL=http://localhost:9200
ELASTICSEARCH_API_KEY=
```

For Elastic Cloud use its HTTPS endpoint and API key. Do not disable TLS verification. The implementation uses the official Python `elasticsearch` client installed by `requirements.txt`.

Test connectivity without printing credentials:

```bash
python scripts/test_elasticsearch_connection.py
```

### Initialize and seed indices

The catalog uses:

- `products-v1` for canonical structured product records
- `product-evidence-v1` for local evidence chunks
- `product-evaluations-v1` for optional project-specific evaluation records

Intentional Elasticsearch mutations require `ES_ALLOW_WRITES=1`:

```bash
export ES_ALLOW_WRITES=1
python scripts/init_elasticsearch.py
python scripts/import_products.py
python scripts/import_product_evidence.py
# For source-backed candidates collected by Apify:
python scripts/import_apify_discovery.py DATASET_ID onboard_computer
streamlit run app.py
unset ES_ALLOW_WRITES
```

Initialization creates only missing indices and never deletes existing data. Development reset requires both the write guard and explicit confirmation:

```bash
ES_ALLOW_WRITES=1 python scripts/reset_elasticsearch.py --confirm-reset
```

The tracked development catalog contains 24 clearly labeled `development_sample` records across motor drivers, onboard computers, and LiDAR/ranging sensors, plus 12 low-authority development evidence chunks. These records do not represent verified manufacturer claims.

### Search architecture

A component role is converted deterministically into a `ComponentSearchProfile`. Category, voltage, current, channels, interfaces, operating-system context, milestone criticality, connected components, and budget preferences become structured requirements. Elasticsearch applies exact/range filters and lexical plus semantic ranking. Python then independently evaluates compatibility and computes a transparent project-fit score; search relevance can never override a hard incompatibility.

Mappings prefer Elastic `semantic_text`. If the connected version or inference endpoint cannot support semantic indexing/querying, initialization/import/search fall back to ordinary text and keyword retrieval. The UI explicitly reports keyword fallback. Missing specifications remain unknown rather than becoming zero or false.

Selecting a catalog result copies its identity, expected price, and known structured specifications into the PostgreSQL `ProductSelection`, including the Elastic `product_id`. This keeps the saved project readable and evaluable when Elasticsearch is offline.

### Elasticsearch troubleshooting

- **Product search unavailable:** verify `ELASTICSEARCH_URL`, API-key permissions, and node reachability.
- **Index missing:** run `ES_ALLOW_WRITES=1 python scripts/init_elasticsearch.py`.
- **No results:** inspect the generated hard requirements; exact numeric filters may legitimately exclude every record.
- **Semantic unavailable:** keyword search remains operational; configure a supported inference endpoint if semantic retrieval is required.
- **Import rejected:** confirm mappings exist, inspect invalid-record counts, and verify write permissions.

## Apify live product intelligence

Apify collects approved product pages; Elasticsearch stores append-only observations, latest listing state, changes, and source health; PostgreSQL stores monitored sources, preferences, schedules, and Apify run records. Python performs identity checks, urgency, change detection, deadline analysis, schedule selection, comparison, and recommendations.

### Configure Apify

Create an Apify API token and add the following to `.env`:

```env
APIFY_API_TOKEN=your_token
APIFY_PRODUCT_MONITOR_ACTOR_ID=your_actor_id
APIFY_PRODUCT_ANALYSIS_ACTOR_ID=apify/google-search-scraper
APIFY_PRODUCT_ANALYSIS_COUNTRY=us
APIFY_PRODUCT_ANALYSIS_TIMEOUT_SECS=120
APIFY_WEBHOOK_SECRET=your_random_webhook_secret
APIFY_WEBHOOK_BASE_URL=https://your-app.example.com
APIFY_DEFAULT_BUILD=latest
APIFY_MAX_RUN_COST_USD=1.00
APPROVED_PRODUCT_DOMAINS=supplier.example,manufacturer.example
```

Test authentication without exposing the token:

```bash
python scripts/test_apify_connection.py
```

The **Analyze** action on each **Find Products** result runs Apify's official Google Search Results Scraper with one bounded query, then displays normalized evidence links and the Actor dataset output. Override `APIFY_PRODUCT_ANALYSIS_ACTOR_ID` only with a reviewed Actor that accepts the same input/output contract.

### Deploy the Actor

The Python Actor is in `actors/product_page_monitor/`. It prefers JSON-LD Product data, uses reviewed selectors as fallback, enforces an approved-domain allowlist, preserves unknowns as null, and emits structured failures instead of turning scrape failures into out-of-stock observations.

Using the Apify CLI after authenticating:

```bash
cd actors/product_page_monitor
apify push
cd ../..
```

Set the returned Actor ID as `APIFY_PRODUCT_MONITOR_ACTOR_ID`. Actor input and dataset contracts are documented by `input_schema.json` and `dataset_schema.json`. Reusable reviewed Task and schedule configurations can be created with:

```bash
python scripts/create_apify_tasks.py path/to/reviewed-task.json
python scripts/create_apify_schedules.py path/to/reviewed-schedule.json
```

Do not pass arbitrary user domains. Tasks should hold stable supplier selectors, currency, headers, rate limits, and approved-domain configuration; runs should override only project/product IDs and reviewed URLs.

### Apply monitoring storage and Elasticsearch mappings

```bash
python scripts/init_database.py
export ES_ALLOW_WRITES=1
python scripts/init_elasticsearch.py
unset ES_ALLOW_WRITES
```

Migration `002_add_product_monitoring.sql` adds monitored sources, Apify runs, and component preferences. Elasticsearch adds append-only observations, deterministic latest state, change events, source health, and identity quarantine indices.

### Webhook service

Streamlit does not receive webhooks. Run the dedicated FastAPI service behind HTTPS:

```bash
uvicorn api.apify_webhook:app --host 0.0.0.0 --port 8000
```

Configure an Apify Actor-run webhook for:

```text
POST https://your-app.example.com/webhooks/apify/actor-run
X-Apify-Webhook-Secret: your_random_webhook_secret
```

The endpoint authenticates the secret, claims each run once in PostgreSQL, retrieves the completed dataset, validates observations, verifies exact product identity, quarantines mismatches, appends history, updates latest state, creates changes, updates source health, and reconciles monitoring tier changes. Duplicate deliveries return without duplicate observations or events.

For local webhook testing, expose the FastAPI port with a reviewed HTTPS tunnel and use a dedicated test Actor/source. Never expose Streamlit as a webhook endpoint.

### Monitoring priority and refresh flow

The **Live Products** workspace tab orders roles by deterministic urgency. Deadline pressure, milestone criticality, dependency centrality, procurement gap, replacement difficulty, integration risk, necessity confidence, availability, and delivery margin drive urgency. Tiers range from hourly Critical monitoring to five-day Minimal monitoring. Received and verified products are reduced to infrequent commercial monitoring.

**Refresh now** starts one asynchronous Actor or Task run and stores the run ID. Simultaneous source runs are rejected. The UI returns immediately; webhook ingestion updates observations later. Stale source data forces a refresh recommendation before purchasing decisions.

Deadline-aware comparison never promotes incompatible products. Low urgency emphasizes cost; high urgency increases availability, delivery, and integration weights. Recommendations include order now, order soon, monitor, choose an alternative, verify compatibility, wait for price, defer optional work, refresh stale data, manual review, or no action, with supporting facts and change explanations.

### Cost and safety guidance

- Set `APIFY_MAX_RUN_COST_USD` conservatively.
- Keep `maximum_requests` small and source delays respectful.
- Use shared Tasks rather than one Actor per product.
- Increase schedules only when the calculated tier changes.
- Reduce repeatedly failing sources and received/verified products.
- Never infer availability from scrape failure, price from missing text, or delivery dates from vague shipping language.
- Require `ES_ALLOW_WRITES=1` for initialization, imports, webhook ingestion, and acknowledgments.

### Apify troubleshooting

- **Actor missing:** deploy `actors/product_page_monitor` and set its ID.
- **Authentication failure:** rotate `APIFY_API_TOKEN` and rerun the connection test.
- **No observations:** inspect the Apify run dataset and structured extraction errors.
- **Identity mismatch:** review the quarantine record and expected part number/model; do not merge semantically.
- **Webhook rejected:** verify the HTTPS URL and `X-Apify-Webhook-Secret` header.
- **Changes absent:** confirm Elasticsearch writes are enabled for the webhook process and monitoring indices exist.

## Project layout

```text
app.py
requirements.txt
.env.example
api/apify_webhook.py
actors/product_page_monitor/
db/migrations/001_create_projects.sql
models/
  project.py
  persistence.py
  readiness.py
pages/
  home.py
  project_workspace.py
  overview.py
  blueprint.py
  bom.py
  component_detail.py
  find_products.py
  live_products.py
  settings.py
repositories/
  database.py
  exceptions.py
  project_repository.py
scripts/
  init_database.py
  test_database_connection.py
  migrate_sqlite_projects.py
services/
  readiness.py
  validation.py
  bom_calculator.py
  graph_builder.py
  graph_analysis.py
  project_operations.py
  project_summary.py
  export_service.py
  elasticsearch_client.py
  search_profile.py
  product_search.py
  compatibility.py
  product_ranking.py
  product_evidence_search.py
  product_selection.py
  apify_client.py
  component_urgency.py
  monitoring_scheduler.py
  observation_ingestion.py
  product_change_detection.py
  procurement_recommendation.py
ui/
tests/
examples/autonomous_target_rover.json
```

## Troubleshooting

### `DATABASE_URL is missing`

Create `.env` in the repository root and add `DATABASE_URL`. Run commands from the repository root so `python-dotenv` can find it.

### `Unable to connect to PostgreSQL`

Confirm PostgreSQL is running, the role/password are correct, and the host and port are reachable:

```bash
python scripts/test_database_connection.py
```

### `Database table has not been initialized`

Run:

```bash
python scripts/init_database.py
```

### Authentication or ownership errors

Connect as an administrator and confirm `bom_app` owns the database or has table privileges. Do not put an administrator URL in the application `.env`.

### Integration tests are skipped

Set `TEST_DATABASE_URL` to the isolated database. This is intentionally separate from `DATABASE_URL`.

### Existing SQLite data does not appear

PostgreSQL does not read the old SQLite file. Run the optional migration script explicitly.
