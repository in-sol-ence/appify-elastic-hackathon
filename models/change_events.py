from pydantic import BaseModel
class ChangeSeverity(BaseModel): severity:str;score:float;explanation:str
