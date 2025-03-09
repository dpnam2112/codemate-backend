from uuid import UUID
from typing import Optional
from pydantic import BaseModel
from core.repository.enum import ActivityType

class AddActivityRequest(BaseModel):
    type: ActivityType
    description: str
