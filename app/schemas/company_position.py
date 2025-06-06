from pydantic import BaseModel, Field
from uuid import UUID
from typing import Optional

class CompanyPositionCreate(BaseModel):
    position_code: str
    position_name: str
    position_detail: Optional[str] = None

class CompanyPositionRead(BaseModel):
    position_id: UUID
    position_code: str
    position_name: str
    position_detail: Optional[str] = None

    class Config:
        orm_mode = True
