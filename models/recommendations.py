from datetime import datetime
from typing import Literal
from pydantic import BaseModel,Field
RecommendationAction=Literal['order_now','order_soon','continue_monitoring','select_alternative','verify_compatibility','wait_for_better_price','defer_optional_component','refresh_stale_data','manual_review_required','no_action']
class ProcurementRecommendation(BaseModel):
 action:RecommendationAction;priority:str;reason:str;supporting_facts:list[str]=Field(default_factory=list);confidence:float=Field(ge=0,le=1);expires_at:datetime;remaining_uncertainty:list[str]=Field(default_factory=list);previous_action:RecommendationAction|None=None;change_explanation:list[str]=Field(default_factory=list)
