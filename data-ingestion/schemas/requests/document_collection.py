from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class CreateDocumentCollectionRequest(BaseModel):
    """Pydantic model for creating/updating a DocumentCollection."""
    name: str
    description: Optional[str] = None
