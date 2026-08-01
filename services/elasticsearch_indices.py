from services.elasticsearch_client import (
    CHANGE_EVENTS_INDEX, CURRENT_LISTINGS_INDEX, EVALUATIONS_INDEX,
    EVIDENCE_INDEX, OBSERVATIONS_INDEX, PRODUCTS_INDEX, QUARANTINE_INDEX,
    SOURCE_HEALTH_INDEX,
)
KEYWORDS=["product_id","manufacturer","model","manufacturer_part_number","category","subcategory","motor_types","control_interfaces","communication_interfaces","supported_operating_systems","supported_software","currency","lifecycle_status","source_type"]
NUMBERS=["input_voltage_min_v","input_voltage_max_v","continuous_current_a","continuous_current_per_channel_a","peak_current_a","peak_current_per_channel_a","power_w","weight_g","length_mm","width_mm","height_mm","price_estimate","specification_confidence"]
PRODUCTS_MAPPING={"mappings":{"dynamic":"strict","properties":{**{f:{"type":"keyword"} for f in KEYWORDS},**{f:{"type":"float"} for f in NUMBERS},"channel_count":{"type":"integer"},"documentation_available":{"type":"boolean"},**{f:{"type":"text"} for f in ["name","description","product_summary","intended_applications","important_features","source_url"]},"semantic_text":{"type":"semantic_text"},"created_at":{"type":"date"},"updated_at":{"type":"date"}}}}
EVIDENCE_MAPPING={"mappings":{"dynamic":"strict","properties":{**{f:{"type":"keyword"} for f in ["evidence_id","product_id","manufacturer","product_model","source_type","hardware_revision","firmware_version","operating_system","software_version"]},"title":{"type":"text"},"text":{"type":"text"},"semantic_text":{"type":"semantic_text"},"source_authority":{"type":"float"},"source_url":{"type":"keyword","ignore_above":2048},"published_at":{"type":"date"},"collected_at":{"type":"date"}}}}
EVALUATIONS_MAPPING={"mappings":{"dynamic":"strict","properties":{**{f:{"type":"keyword"} for f in ["evaluation_id","project_id","component_role_id","product_id","compatibility_status","hard_requirements_passed","hard_requirements_failed","unknown_requirements","failure_reasons","warnings","evidence_ids"]},"search_score":{"type":"float"},"project_fit_score":{"type":"float"},"evaluated_at":{"type":"date"}}}}
OBSERVATION_PROPERTIES={
 "@timestamp":{"type":"date"},
 **{f:{"type":"keyword"} for f in ["observation_id","schema_version","monitoring_job_id","project_id","component_role_id","product_id","source_id","actor_run_id","source_type","supplier"]},
 "source_url":{"type":"keyword","ignore_above":2048},
 "identity":{"properties":{**{f:{"type":"keyword"} for f in ["title","manufacturer","model","manufacturer_part_number","supplier_sku"]}}},
 "commercial":{"properties":{"price":{"type":"float"},"original_price":{"type":"float"},"currency":{"type":"keyword"},"availability":{"type":"keyword"},"inventory_quantity":{"type":"integer"},"delivery_text":{"type":"text"},"delivery_earliest":{"type":"date"},"delivery_latest":{"type":"date"}}},
 "product_state":{"properties":{"revision":{"type":"keyword"},"lifecycle_status":{"type":"keyword"}}},
 "evidence":{"type":"object","enabled":False},
 "extraction":{"properties":{"status":{"type":"keyword"},"confidence":{"type":"float"},"warnings":{"type":"text"},"error_category":{"type":"keyword"},"error_message":{"type":"text"}}},
 "ingestion_timestamp":{"type":"date"},
}
OBSERVATIONS_MAPPING={"mappings":{"dynamic":"strict","properties":OBSERVATION_PROPERTIES}}
CHANGE_MAPPING={"mappings":{"dynamic":"strict","properties":{**{f:{"type":"keyword"} for f in ["event_id","project_id","component_role_id","product_id","source_id","event_type","event_severity","acknowledgment_status"]},"previous_value":{"type":"object","enabled":False},"current_value":{"type":"object","enabled":False},"change_magnitude":{"type":"float"},"observed_at":{"type":"date"},"component_urgency_score":{"type":"float"},"source_confidence":{"type":"float"},"supporting_observation_ids":{"type":"keyword"}}}}
SOURCE_HEALTH_MAPPING={"mappings":{"dynamic":"strict","properties":{**{f:{"type":"keyword"} for f in ["source_id","data_freshness_status","actor_run_id","error_category"]},"last_successful_run":{"type":"date"},"last_failure":{"type":"date"},"last_verified_observation":{"type":"date"},"consecutive_failures":{"type":"integer"},"extraction_confidence":{"type":"float"}}}}
INDEX_MAPPINGS={PRODUCTS_INDEX:PRODUCTS_MAPPING,EVIDENCE_INDEX:EVIDENCE_MAPPING,EVALUATIONS_INDEX:EVALUATIONS_MAPPING,OBSERVATIONS_INDEX:OBSERVATIONS_MAPPING,CURRENT_LISTINGS_INDEX:OBSERVATIONS_MAPPING,CHANGE_EVENTS_INDEX:CHANGE_MAPPING,SOURCE_HEALTH_INDEX:SOURCE_HEALTH_MAPPING,QUARANTINE_INDEX:{"mappings":{"dynamic":True}}}
