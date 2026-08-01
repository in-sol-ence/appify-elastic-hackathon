from datetime import datetime

from pydantic import BaseModel


class ProjectSummary(BaseModel):
    project_id: str
    project_name: str
    status: str
    created_at: datetime
    updated_at: datetime
