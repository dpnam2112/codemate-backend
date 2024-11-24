from typing import Annotated, Optional
from uuid import UUID
from langchain_core.runnables import RunnableConfig
import neo4j
from langchain_core.embeddings import Embeddings
from machine.providers.ai_tool import AIToolProvider, EmbeddingsModelName
from machine.providers.db_session import DBSessionProvider
from langchain_core.tools import InjectedToolArg, tool
from .schemas import AddLearningResource
from core.logger import syslog

def get_learner_profile_and_learning_resources(
    user_id: str, concepts: list[str], top_n: int = 10, similarity_threshold: float = 0.9
):
    """
    Retrieves a learner's profile and the top N learning resources based on similarity to the learner's profile,
    including semantically related concepts.

    Args:
        user_id (str): The unique identifier of the learner.
        concepts (list[str]): A list of concept names.
        top_n (int): The number of top learning resources to return.
        similarity_threshold (float): The minimum similarity score to consider a concept related.

    Returns:
        dict: A dictionary containing the learner's profile and the top N learning resources.
    """
    embeddings_model = AIToolProvider().embedding_models_factory(EmbeddingsModelName.GOOGLE_TEXT_EMBEDDING)

    # Step 1: Compute embeddings for the input concepts
    concept_embeddings = [
        {"name": concept, "embedding": embeddings_model.embed_query(concept)}
        for concept in concepts
    ]

    with DBSessionProvider().get_neo4j_session() as session:
        query = """
        UNWIND $concept_embeddings AS input
        MATCH (concept:Concept)
        WHERE vector.similarity.cosine(concept.embedding, input.embedding) > $threshold
        WITH concept

        // match and calculate the learner's proficiency vector
        OPTIONAL MATCH (learner {id: $user_id})-[learn:LEARN]->(concept)
        WITH learner,
             concept,
             CASE
                WHEN learn IS NULL THEN 0
                ELSE coalesce(learn.proficiency, 0)
             END AS proficiency
        WITH learner, collect(concept) AS concepts, collect(proficiency) AS proficiencies

        UNWIND concepts AS concept
        MATCH (resource:LearningResource)
        OPTIONAL MATCH (resource)-[cover:COVER]->(concept)
        WITH learner,
             concepts,
             proficiencies,
             resource,
             CASE
                WHEN cover IS NULL THEN 0
                ELSE coalesce(cover.difficulty, 0)
             END AS difficulty

        WITH learner,
             concepts,
             proficiencies, 
             resource,  // Group by resource to get its difficulty vector
             collect(difficulty) AS difficulties  // Fill missing difficulties with 0

        // Calculate the suitability between learner's proficiency vector and resource's difficulty vector
        WITH learner, 
             concepts,
             resource, 
             proficiencies, 
             difficulties, 
             vector.similarity.euclidean(proficiencies, difficulties) AS similarity  // Cosine similarity between vectors

        // Return results: learner, learning resources, and similarity
        RETURN learner, [concept IN concepts | concept.name] AS concepts,
               proficiencies, 
               resource,
               difficulties, 
               similarity
        ORDER BY similarity DESC
        LIMIT $top_n
        """

        combined_data = list(session.run(
                query,
                concept_embeddings=concept_embeddings,
                user_id=user_id,
                top_n=top_n,
                threshold=similarity_threshold
            ))

    # Parse results
    learner_profile = {}
    top_resources = []

    # Iterate over the results of the combined query
    for record in combined_data:
        # Update the learner's profile
        if not learner_profile:  # Initialize the learner profile if empty
            learner_profile = {
                concept: proficiency
                for concept, proficiency in zip(record["concepts"], record["proficiencies"])
            }

        # Append learning resource data
        top_resources.append(record["resource"])

    syslog.info("learner_profile:", learner_profile)
    syslog.info("top_resource:", top_resources)

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
            MERGE (r)-[rel:RELATE_TO]->(c)
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
    user_id = config.get("configurable", {}).get("user_id")
    if not isinstance(user_id, str):
        raise ValueError("Invalid type of user_id.")
    return get_learner_profile_and_learning_resources(user_id, concepts)
