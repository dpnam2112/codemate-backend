from typing import Annotated, List, Optional
from uuid import UUID

from pydantic import BaseModel
from langchain_core.runnables import RunnableConfig
import neo4j
from langchain_core.embeddings import Embeddings
from machine.providers.ai_tool import AIToolProvider, EmbeddingsModelName
from machine.providers.db_session import DBSessionProvider
from langchain_core.tools import InjectedToolArg, tool
from .schemas import AddLearningResource, RecommenderItem
from core.logger import syslog

def get_learner_profile_and_resource_related_concepts(
    user_id: str, 
    course_id: str, 
    input_concepts: str,
    top_n: int = 10, 
    similarity_threshold: float = 0.8
):
    """
    Retrieves a learner's profile and the top N learning resources for a specific course,
    considering only concepts directly related to learning resources.

    Args:
        user_id (str): The unique identifier of the learner.
        course_id (str): The unique identifier of the course.
        input_concepts (list[str]): A list of input concept names.
        top_n (int): The number of top learning resources to return.
        similarity_threshold (float): The minimum similarity score to consider a concept related.

    Returns:
        dict: A dictionary containing the learner's profile and the top N learning resources.
    """
    syslog.info("invoke get_learner_profile_and_learning_resources")
    syslog.info("user_id =", user_id)
    syslog.info("course_id =", course_id)
    embeddings_model = AIToolProvider().embedding_models_factory(EmbeddingsModelName.GOOGLE_TEXT_EMBEDDING)

    with DBSessionProvider().get_neo4j_session() as session:
        query = """
        MATCH (course:Course {id: $course_id})-[:HAS_RESOURCE]->(resource:LearningResource)
        MATCH (resource)-[:COVER]->(concept:Concept)

        // Collect relevant concepts and learner's proficiency
        WITH resource, concept
        OPTIONAL MATCH (learner {id: $user_id})-[learn:LEARN]->(concept)
        WITH resource, concept,
             CASE
                WHEN learn IS NULL THEN 0
                ELSE coalesce(learn.proficiency, 0)
             END AS proficiency
        WITH resource, collect(distinct concept) AS concepts,
             collect(proficiency) AS proficiencies

        // Compute difficulty vectors for the resources
        UNWIND concepts AS concept
        OPTIONAL MATCH (resource)-[cover:COVER]->(concept)
        WITH resource, concepts, proficiencies,
             CASE
                WHEN cover IS NULL THEN 0
                ELSE coalesce(cover.difficulty, 0)
             END AS difficulty
        WITH resource, concepts, proficiencies,
             collect(difficulty) AS difficulties

        // Calculate similarity between learner's proficiency vector and resource's difficulty vector
        WITH resource, concepts, proficiencies, difficulties, vector.similarity.euclidean(proficiencies, difficulties) AS similarity ORDER BY similarity DESC
        LIMIT $top_n

        // Return results
        RETURN resource, concepts, proficiencies, difficulties, similarity
        """
        
        combined_data = list(session.run(
            query,
            course_id=course_id,
            user_id=user_id,
            top_n=top_n,
            threshold=similarity_threshold
        ))

    # Parse results
    learner_profile = {}
    top_resources = []

    for record in combined_data:
        # Initialize learner profile if empty
        if not learner_profile:
            learner_profile = {
                concept["name"]: proficiency
                for concept, proficiency in zip(record["concepts"], record["proficiencies"])
            }
        # Append learning resource data
        top_resources.append(dict(record["resource"]))

    syslog.info("learner_profile:", learner_profile)
    syslog.info("top_resources:", top_resources)

    return {
        "learner_profile": learner_profile,
        "top_resources": top_resources,
    }

@DBSessionProvider().inject_neo4j_session(argname="neo4j_session")
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

@tool
def get_learner_profile_and_learning_resources_tool(
    concepts: list[str],
    config: RunnableConfig
):
    """
    ## Purpose

    The function aims to:

        Understand the learner's knowledge state based on their proficiency in various concepts.
        Recommend learning resources that are well-matched to the learner’s current skill level, calculated through a similarity metric between the learner's proficiency and the difficulty of learning resources.
    """

    user_id = config.get("configurable", {}).get("user_id")
    course_id = config.get("configurable", {}).get("course_id")

    if not isinstance(user_id, str):
        raise ValueError("Invalid type of user_id.")

    if not isinstance(course_id, str):
        raise ValueError("Invalid type of course_id.")

    return get_learner_profile_and_resource_related_concepts(user_id, course_id, concepts)

class lp_recommender_response(BaseModel):
    """Retrieves a learner's profile and the top N learning resources for a specific course,
    considering only concepts directly related to learning resources."""
    recommended_items: List[RecommenderItem]
