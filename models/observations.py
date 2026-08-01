from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field

class Availability(str,Enum):
 IN_STOCK="in_stock";LIMITED_STOCK="limited_stock";BACKORDER="backorder";PREORDER="preorder";OUT_OF_STOCK="out_of_stock";DISCONTINUED="discontinued";UNKNOWN="unknown"
class ExtractionStatus(str,Enum): SUCCESS="success";FAILED="failed";PARTIAL="partial";MISSING="missing"
class ObservationIdentity(BaseModel):
 title:str|None=None;manufacturer:str|None=None;model:str|None=None;manufacturer_part_number:str|None=None;supplier_sku:str|None=None
class CommercialObservation(BaseModel):
 price:float|None=Field(default=None,ge=0);original_price:float|None=Field(default=None,ge=0);currency:str|None=None
 availability:Availability=Availability.UNKNOWN;inventory_quantity:int|None=Field(default=None,ge=0);delivery_text:str|None=None;delivery_earliest:datetime|None=None;delivery_latest:datetime|None=None
class ProductStateObservation(BaseModel): revision:str|None=None;lifecycle_status:str|None=None
class ObservationEvidence(BaseModel): content_hash:str|None=None;price_text:str|None=None;availability_text:str|None=None;shipping_text:str|None=None;raw:dict[str,Any]=Field(default_factory=dict)
class ExtractionResult(BaseModel): status:ExtractionStatus;confidence:float=Field(default=0,ge=0,le=1);warnings:list[str]=Field(default_factory=list);error_category:str|None=None;error_message:str|None=None
class ProductObservation(BaseModel):
 schema_version:str="1.0";monitoring_job_id:str;project_id:str;component_role_id:str;product_id:str;source_id:str;actor_run_id:str
 observed_at:datetime;source_type:str;source_url:str;supplier:str|None=None;identity:ObservationIdentity=Field(default_factory=ObservationIdentity)
 commercial:CommercialObservation=Field(default_factory=CommercialObservation);product_state:ProductStateObservation=Field(default_factory=ProductStateObservation)
 evidence:ObservationEvidence=Field(default_factory=ObservationEvidence);extraction:ExtractionResult
 ingestion_timestamp:datetime=Field(default_factory=lambda:datetime.now(timezone.utc))
class ProductChangeEvent(BaseModel):
 event_id:str;project_id:str;component_role_id:str;product_id:str;source_id:str;event_type:str;previous_value:Any=None;current_value:Any=None;change_magnitude:float|None=None;observed_at:datetime;component_urgency_score:float=0;event_severity:str="Low";source_confidence:float=0;supporting_observation_ids:list[str]=Field(default_factory=list);acknowledgment_status:str="unacknowledged"
