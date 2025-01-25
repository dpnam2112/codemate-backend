from pydantic import BaseModel

class RecommenderOutputSchema(BaseModel):
    id: str
    code: str
    lr_description: str
    explanation: str
