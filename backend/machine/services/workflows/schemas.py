from uuid import UUID
from pydantic import BaseModel, Field
from typing import List

class LearnerConceptProficiency(BaseModel):
    concept: str
    proficiency: float

class LearningResourceRecommendation(BaseModel):
    resource_id: str
    similarity: float

class BestMatchLearningResourceResponse(BaseModel):
    learner_profile: LearnerConceptProficiency
    learning_resources: LearningResourceRecommendation

class LearningResourceConceptRelationship(BaseModel):
    """
    Used to represent the relationship between a learning resource and its related concepts.
    
    Attributes:
        difficulty (float): Represents the difficulty level of the concept in relation to the learning resource. 
            Higher values indicate a more challenging concept, helping tailor resource recommendations to learners’ proficiency levels.
        relevance (float): Indicates how closely related or essential the concept is to the learning resource. 
            Higher values suggest a core concept, while lower values might indicate supplementary or less central concepts.

    Returns:
        A dictionary containing the parameters. Here is an example:
        {
            "concept": "",
            "difficulty": 0.8,
            "relevance": 0.6
        }
    """
    concept: str = Field(..., description="Concept's name.")
    difficulty: float = Field(..., description="Represents the difficulty level of the concept in relation to the learning resource.")
    relevance: float = Field(..., description="Indicates how essential the concept is to the learning resource.")

class AddLearningResource(BaseModel):
    """Add a new learning resource (which can be a lesson, a module, or an exercise, .etc to the
    graph database."""
    title: str = Field(..., description="Title of the learning resource")
    code: str = Field(..., description="A unique code for a learning resource. E.g, if a learning resource is a lesson, then its code may be 'lesson_C193E87'")
    description: str = Field(..., description="Learning resource's description.")
    type: str = Field(..., description="Learning resource's type. For example: reading, multiple-choice, writing question, .etc")
    concepts: List[LearningResourceConceptRelationship] = Field(..., description="Concepts relating to the learning resource.")
    learning_outcomes: List[str] = Field(..., description="Learning outcomes that learners will achieve after completing this learning resource")

class RecommenderItem(BaseModel):
    id: str = Field(..., description="id of the recommended learning resource.")
    code: str = Field(..., description="learning resource's code.")
    description: str = Field(..., description="a short description for the learning resource.")
    explanation: str = Field(..., description="explanation for why this learning resource is recommended to the learner based on her profile.")
