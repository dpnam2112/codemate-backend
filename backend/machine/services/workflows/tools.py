from typing import Annotated, List, Optional
from uuid import UUID

from pydantic import BaseModel
from langchain_core.runnables import RunnableConfig
import neo4j
from langchain_core.embeddings import Embeddings
from .ai_tool_provider import AIToolProvider, EmbeddingsModelName
from langchain_core.tools import InjectedToolArg, tool
from .schemas import AddLearningResource, RecommendedLessonItem
from core.logger import syslog
from core.db.neo4j_session import Neo4jDBSessionProvider

def get_learner_profile_and_related_lessons(
    config: RunnableConfig,
    input_concepts: Optional[list[str]] = None,
    fulltext_index_name: str = "conceptNameIndex"
):
    """
    Retrieves a learner's profile and the top N lessons for a specific course.

    Args:
        input_concepts (Optional[list[str]]): A list of concept names to filter by.
        fulltext_index_name (str): The name of the full-text index on Concept.name.

    Returns:
        dict: A dictionary containing the learner's profile and related lessons.
    """
    user_id = config.get("configurable", {}).get("user_id")
    course_id = config.get("configurable", {}).get("course_id")

    syslog.debug("user_id =", user_id)
    syslog.debug("course_id =", course_id)

    with Neo4jDBSessionProvider().get_neo4j_session() as session:
        if input_concepts:
            # Query for specified concepts
            fulltext_query = " OR ".join([f'\"{concept}\"' for concept in input_concepts])
            query = """
            CALL db.index.fulltext.queryNodes($fulltext_index_name, $fulltext_query) YIELD node AS concept, score
            MATCH (course:Course {id: $course_id})-[:HAS_LESSON]->(lesson:Lesson)
            MATCH (lesson)-[:COVER]->(concept)
            OPTIONAL MATCH (learner {id: $user_id})-[learn:LEARN]->(concept)
            WITH learner, lesson, concept.name AS concept_name,
                 coalesce(learn.proficiency, 0) AS proficiency,
                 coalesce((lesson)-[:COVER]->(concept).difficulty, 0) AS difficulty,
                 properties(learner) AS learner_attributes,
                 properties(lesson) AS lesson_attributes
            RETURN learner_attributes,
                   lesson_attributes,
                   collect(DISTINCT {concept: concept_name, difficulty: difficulty}) AS lesson_difficulty,
                   collect(DISTINCT {concept: concept_name, proficiency: proficiency}) AS learner_proficiency
            """
        else:
            # Query for all lessons and concepts
            query = """
            MATCH (course:Course {id: $course_id})-[:HAS_LESSON]->(lesson:Lesson)
            MATCH (lesson)-[cover_rel:COVER]->(concept:Concept)
            OPTIONAL MATCH (learner {id: $user_id})-[learn:LEARN]->(concept)
            WITH learner, lesson, concept.name AS concept_name,
                 coalesce(learn.proficiency, 0) AS proficiency,
                 coalesce(cover_rel.difficulty, 0) AS difficulty,
                 properties(learner) AS learner_attributes,
                 properties(lesson) AS lesson_attributes
            RETURN learner_attributes,
                   lesson_attributes,
                   collect(DISTINCT {concept: concept_name, difficulty: difficulty}) AS lesson_difficulty,
                   collect(DISTINCT {concept: concept_name, proficiency: proficiency}) AS learner_proficiency
            """

        # Execute the query
        result = session.run(
            query,
            fulltext_index_name=fulltext_index_name,
            fulltext_query=fulltext_query if input_concepts else None,
            course_id=course_id,
            user_id=user_id,
        )

    # Parse results
    learner_profile = {}
    lessons = []
    learner_attributes = {}

    records = list(result)

    for record in records:
        # Build learner profile
        learner_profile = {
            entry["concept"]: entry["proficiency"]
            for entry in record["learner_proficiency"]
        }
        # Capture learner attributes
        learner_attributes = record["learner_attributes"]
        # Build lesson data
        lessons.append({
            "lesson_attributes": record["lesson_attributes"],
            "difficulty_mapping": {
                entry["concept"]: entry["difficulty"]
                for entry in record["lesson_difficulty"]
            }
        })

    syslog.debug("Learner profile:", learner_profile)
    syslog.debug("Learner attributes:", learner_attributes)
    syslog.debug("Lessons:", lessons)

    return {
        "learner_profile": learner_profile,
        "learner_attributes": learner_attributes,
        "lessons": lessons,
    }

@Neo4jDBSessionProvider().inject_neo4j_session(argname="neo4j_session")
@AIToolProvider().inject_embeddings_model(
    argname="embeddings_model",
    modelname=EmbeddingsModelName.GOOGLE_TEXT_EMBEDDING
)
def add_learning_resource(
    id_: Annotated[UUID, InjectedToolArg],
    llm_input: AddLearningResource,
    embeddings_model: Annotated[Optional[Embeddings], InjectedToolArg],
    neo4j_session: Annotated[Optional[neo4j.Session], InjectedToolArg]
):
    """
    Adds a new learning resource to the graph database, associating it with concepts and learning outcomes.

    Args:
        id_ (UUID): The unique identifier of the learning resource to be added.
        llm_input (AddLearningResourceInput): Input data containing the description, type, concepts, and learning outcomes for the new learning resource.
        embeddings_model (Optional[Embeddings]): An embedding model used to generate embeddings for concepts and outcomes.
        neo4j_session (Optional[neo4j.Session]): A session to interact with the Neo4j graph database.

    Returns:
        None: The function performs a graph database operation without returning a result.
    """
    assert embeddings_model is not None
    assert neo4j_session is not None

    # Step 1: Generate embeddings for concepts and learning outcomes
    concept_data = [
        {
            "concept": concept.concept,
            "embedding": embeddings_model.embed_query(concept.concept),
            "difficulty": concept.difficulty,
            "relevance": concept.relevance
        }
        for concept in llm_input.concepts
    ]
    
    outcome_data = [(outcome, embeddings_model.embed_query(outcome)) for outcome in llm_input.learning_outcomes]

    # Step 2: Create a single query to add the resource and relationships
    neo4j_session.run(
        """
        // Create the learning resource
        MERGE (r:LearningResource {id: $id, description: $description, type: $type, code: $code})

        // Create or match each concept and create RELATE_TO relationship with difficulty and relevance properties
        FOREACH (data IN $concept_data |
            MERGE (c:Concept {name: data.concept})
            ON CREATE SET c.embedding = data.embedding
            MERGE (r)-[rel:COVER]->(c)
            ON CREATE SET rel.difficulty = data.difficulty, rel.relevance = data.relevance
            ON MATCH SET rel.difficulty = data.difficulty, rel.relevance = data.relevance
        )

        // Create or match each learning outcome and create HAS_OUTCOME relationship
        FOREACH (data IN $outcome_data |
            MERGE (lo:LearningOutcome {name: data[0]})
            ON CREATE SET lo.embedding = data[1]
            MERGE (r)-[:HAS_OUTCOME]->(lo)
        )
        """,
        id=str(id_),
        description=llm_input.description,
        type=llm_input.type,
        code=llm_input.code,
        concept_data=concept_data,
        outcome_data=outcome_data
    )

class LPPlanningWorkflowResponse(BaseModel):
    """Retrieves a learner's profile and the top N learning resources for a specific course,
    considering only concepts directly related to learning resources."""
    recommended_items: List[RecommendedLessonItem]

def get_learner_profile(
    config: RunnableConfig,
    fulltext_index_name: str = "conceptNameIndex"
):
    """
    Retrieves the learner's profile including their attributes and proficiency vector,
    considering only concepts covered by lessons within a specific course.

    Argsget_learner_profile
        config (RunnableConfig): Configuration object containing user information.
        course_id (str): The unique identifier of the course.
        input_concepts (Optional[list[str]]): A list of concept names to filter by. If input_concepts is not specified, learner profile will contain all concepts that the course cover. Must be passed as None.
        fulltext_index_name (str): Name of the full-text index on Concept.name.

    Returns:
        dict: A dictionary containing learner's attributes and proficiency vector.
    """
    user_id = config.get("configurable", {}).get("user_id")
    course_id = config.get("configurable", {}).get("course_id")

    syslog.debug("user_id =", user_id)
    syslog.debug("course_id =", course_id)

    input_concepts = []

    with Neo4jDBSessionProvider().get_neo4j_session() as session:
        if input_concepts:
            # Query for specified concepts covered by lessons in the course
            fulltext_query = " OR ".join([f'\"{concept}\"' for concept in input_concepts])
            query = """
            CALL db.index.fulltext.queryNodes($fulltext_index_name, $fulltext_query) YIELD node AS concept, score
            MATCH (course:Course {id: $course_id})-[:HAS_LESSON]->(lesson:Lesson)-[:COVER]->(concept)
            OPTIONAL MATCH (learner {id: $user_id})-[learn:LEARN]->(concept)
            RETURN properties(learner) AS learner_attributes,
                   collect(DISTINCT {concept: concept.name, proficiency: coalesce(learn.proficiency, 0)}) AS learner_proficiency
            """
            params = {
                "fulltext_index_name": fulltext_index_name,
                "fulltext_query": fulltext_query,
                "course_id": course_id,
                "user_id": user_id,
            }
        else:
            # Query for all concepts covered by lessons in the course
            query = """
            MATCH (course:Course {id: $course_id})-[:HAS_LESSON]->(lesson:Lesson)-[:COVER]->(concept:Concept)
            OPTIONAL MATCH (learner {id: $user_id})-[learn:LEARN]->(concept)
            RETURN properties(learner) AS learner_attributes,
                   collect(DISTINCT {concept: concept.name, proficiency: coalesce(learn.proficiency, 0)}) AS learner_proficiency
            """
            params = {
                "course_id": course_id,
                "user_id": user_id,
            }

        result = session.run(query, **params)
        records = list(result)


    learner_attributes = {}
    learner_proficiencies = {}

    syslog.debug("records =", records)

    for record in records:
        # Check if the learner attributes exist in the record
        if record["learner_attributes"] is not None:
            # Extract all learner attributes
            learner_attributes = {
                key: value for key, value in record["learner_attributes"].items()
            }
            syslog.debug(f"Learner attributes found: {learner_attributes}")
        else:
            # No learner node found, keep learner_attributes empty
            syslog.debug("No learner node found in record.")

        # Build the learner proficiency mapping
        for entry in record["learner_proficiency"]:
            concept = entry["concept"]
            proficiency = entry["proficiency"]
            learner_proficiencies[concept] = proficiency

    # Add 'proficiencies' key to the learner attributes dictionary
    learner_attributes["proficiencies"] = learner_proficiencies

    syslog.debug(f"Processed learner profile: {learner_proficiencies}")
    syslog.debug(f"Processed learner attributes with proficiencies: {learner_attributes}")

    return learner_attributes


def get_related_lessons(config: RunnableConfig, fulltext_index_name: str = "conceptNameIndex"):
    """
    Retrieves lessons with their attributes and difficulty vector.

    Args:
        config (RunnableConfig): Configuration object containing user and course information.
        fulltext_index_name (str): Name of the full-text index on Concept.name.

    Returns:
        list[dict]: A list of lessons with their attributes and difficulty vectors.
    """
    course_id = config.get("configurable", {}).get("course_id")
    syslog.debug("course_id =", course_id)

    input_concepts = []

    with Neo4jDBSessionProvider().get_neo4j_session() as session:
        if input_concepts:
            fulltext_query = " OR ".join([f'\"{concept}\"' for concept in input_concepts])
            query = """
            CALL db.index.fulltext.queryNodes($fulltext_index_name, $fulltext_query) YIELD node AS concept, score
            MATCH (course:Course {id: $course_id})-[:HAS_LESSON]->(lesson:Lesson)
            MATCH (lesson)-[:COVER]->(concept)
            RETURN properties(lesson) AS lesson_attributes,
                   collect(DISTINCT {concept: concept.name, difficulty: coalesce((lesson)-[:COVER]->(concept).difficulty, 0)}) AS lesson_difficulty
            """
        else:
            query = """
            MATCH (course:Course {id: $course_id})-[:HAS_LESSON]->(lesson:Lesson)
            MATCH (lesson)-[cover_rel:COVER]->(concept:Concept)
            RETURN properties(lesson) AS lesson_attributes,
                   collect(DISTINCT {concept: concept.name, difficulty: coalesce(cover_rel.difficulty, 0)}) AS lesson_difficulty
            """

        result = session.run(
            query,
            fulltext_index_name=fulltext_index_name,
            fulltext_query=fulltext_query if input_concepts else None,
            course_id=course_id,
        )

        records = list(result)

    lessons = []

    for record in records:
        lessons.append({
            "lesson_attributes": record["lesson_attributes"],
            "difficulty_mapping": {
                entry["concept"]: entry["difficulty"]
                for entry in record["lesson_difficulty"]
            }
        })

    syslog.debug("Lessons:", lessons)
    return lessons
