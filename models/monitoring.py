from datetime import datetime
from pydantic import BaseModel,Field

class MonitoredProductSource(BaseModel):
 id:str;project_id:str;component_role_id:str;product_id:str;source_type:str="supplier_product_page";source_url:str;supplier_name:str|None=None;apify_actor_id:str|None=None;apify_task_id:str|None=None;apify_schedule_id:str|None=None;monitoring_enabled:bool=True;monitoring_tier:str="Low";last_successful_run_at:datetime|None=None;last_failed_run_at:datetime|None=None;last_observation_at:datetime|None=None;consecutive_failures:int=0;created_at:datetime|None=None;updated_at:datetime|None=None
class MonitoringPreference(BaseModel):
 id:str;project_id:str;component_role_id:str;enabled:bool=True;minimum_monitoring_tier:str|None=None;maximum_monitoring_tier:str|None=None;user_override_frequency_hours:int|None=None;monitor_price:bool=True;monitor_availability:bool=True;monitor_shipping:bool=True;monitor_product_changes:bool=True
class ApifyRunRecord(BaseModel):
 id:str;apify_run_id:str;monitoring_source_id:str|None=None;project_id:str;component_role_id:str|None=None;product_id:str|None=None;run_type:str;status:str;default_dataset_id:str|None=None;started_at:datetime|None=None;finished_at:datetime|None=None;items_received:int|None=None;error_message:str|None=None;ingestion_status:str="pending"
class ComponentProcurementState(BaseModel):
 availability:str="unknown";expected_delivery_date:datetime|None=None;known_lead_time_days:int|None=None;integration_buffer_days:int|None=None;valid_alternatives:int=0;last_observation_at:datetime|None=None;source_confidence:float=0;active_sellers:int=0;selected_product_id:str|None=None;purchase_status:str="Not planned";verification_status:str="Unverified"
