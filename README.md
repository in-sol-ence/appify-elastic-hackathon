# Robotics BOM Guardian

A Streamlit application for creating, understanding, editing, and deterministically evaluating robotics projects and bills of materials. Projects are validated with Pydantic v2 and persisted as complete JSONB documents in PostgreSQL through Psycopg 3.

This version does not implement monitoring, authentication, alerts, Apify ingestion, or Elasticsearch synchronization.

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

## Project layout

```text
app.py
requirements.txt
.env.example
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
