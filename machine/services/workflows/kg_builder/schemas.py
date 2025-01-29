from pydantic import BaseModel, Field


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

class Course(BaseModel):
    id: str = Field(..., description="Unique id of the course, this can be viewed as surrogate key.")
    title: str = Field(..., description="Title of the course.")
    description: str = Field(..., description="Course's description.")
    concepts: list[LearningResourceConceptRelationship] = Field(..., description="Concepts relating to the learning resource.")
    learning_outcomes: list[str] = Field(..., description="Learning outcomes that learners will achieve after completing this coruse.")


class CourseLesson(BaseModel):
    id: str = Field(..., description="Unique id of the lesson, this can be viewed as surrogate key.")
    title: str = Field(..., description="Title of the learning resource")
    code: str = Field(..., description="A unique code for a learning resource. E.g, if a learning resource is a lesson, then its code may be 'lesson_C193E87'")
    description: str = Field(..., description="Learning resource's description.")
    concepts: list[LearningResourceConceptRelationship] = Field(..., description="Concepts relating to the learning resource.")
    learning_outcomes: list[str] = Field(..., description="Learning outcomes that learners will achieve after completing this learning resource")
