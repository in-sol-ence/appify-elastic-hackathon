CREATE TABLE IF NOT EXISTS monitored_product_sources (
 id UUID PRIMARY KEY, project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
 component_role_id UUID NOT NULL, product_id TEXT NOT NULL, source_type TEXT NOT NULL,
 source_url TEXT NOT NULL, supplier_name TEXT, apify_actor_id TEXT, apify_task_id TEXT,
 apify_schedule_id TEXT, monitoring_enabled BOOLEAN NOT NULL DEFAULT TRUE,
 monitoring_tier TEXT NOT NULL CHECK (monitoring_tier IN ('Critical','High','Medium','Low','Minimal')),
 last_successful_run_at TIMESTAMPTZ, last_failed_run_at TIMESTAMPTZ,
 last_observation_at TIMESTAMPTZ, consecutive_failures INTEGER NOT NULL DEFAULT 0,
 created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
 updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
 UNIQUE(project_id, component_role_id, product_id, source_url)
);
CREATE INDEX IF NOT EXISTS idx_monitored_sources_project ON monitored_product_sources(project_id);
CREATE INDEX IF NOT EXISTS idx_monitored_sources_role ON monitored_product_sources(component_role_id);

CREATE TABLE IF NOT EXISTS apify_runs (
 id UUID PRIMARY KEY, apify_run_id TEXT UNIQUE NOT NULL,
 monitoring_source_id UUID REFERENCES monitored_product_sources(id) ON DELETE SET NULL,
 project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
 component_role_id UUID, product_id TEXT, run_type TEXT NOT NULL, status TEXT NOT NULL,
 default_dataset_id TEXT, started_at TIMESTAMPTZ, finished_at TIMESTAMPTZ,
 items_received INTEGER, error_message TEXT, ingestion_status TEXT NOT NULL DEFAULT 'pending',
 created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
 updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_apify_runs_project ON apify_runs(project_id, created_at DESC);

CREATE TABLE IF NOT EXISTS product_monitoring_preferences (
 id UUID PRIMARY KEY, project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
 component_role_id UUID NOT NULL, enabled BOOLEAN NOT NULL DEFAULT TRUE,
 minimum_monitoring_tier TEXT, maximum_monitoring_tier TEXT,
 user_override_frequency_hours INTEGER CHECK (user_override_frequency_hours > 0),
 monitor_price BOOLEAN NOT NULL DEFAULT TRUE, monitor_availability BOOLEAN NOT NULL DEFAULT TRUE,
 monitor_shipping BOOLEAN NOT NULL DEFAULT TRUE, monitor_product_changes BOOLEAN NOT NULL DEFAULT TRUE,
 created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
 updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
 UNIQUE(project_id, component_role_id)
);
