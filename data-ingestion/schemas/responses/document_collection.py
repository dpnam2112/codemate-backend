from uuid import UUID
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class DocumentCollectionResponse(BaseModel):
    """Pydantic model for returning a DocumentCollection."""
    id: UUID
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)  # Enables ORM mode

