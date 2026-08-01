from datetime import datetime
from pydantic import BaseModel,Field
class ComponentUrgency(BaseModel):
 score:float=Field(ge=0,le=100);level:str;contributing_factors:dict[str,float]=Field(default_factory=dict);days_until_required:int|None=None;schedule_margin_days:int|None=None;explanation:list[str]=Field(default_factory=list)
class MonitoringScheduleDecision(BaseModel): tier:str;frequency_hours:int;reason:str;changed:bool=False
