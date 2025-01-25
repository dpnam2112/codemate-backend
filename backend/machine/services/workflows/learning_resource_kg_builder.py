from enum import StrEnum
from typing import List, Literal
from uuid import uuid4
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field
from core.db.neo4j_session import Neo4jDBSessionProvider
from core.logger import syslog
from .tools import add_learning_resource
from neo4j import AsyncSession as Neo4jAsyncSession


class LearningResourceKGBuilder:
    class LearningResourceType(StrEnum):
        LESSON = "Lesson"
        EXERCISE = "Exercise"
        READING_MATERIAL = "ReadingMaterial"

    class LearningResource(BaseModel):
        title: str = Field(...)
        description: str = Field(...) 
        concepts: list[str] = Field(...)

    def __init__(
        self,
        base_llm_model
    ):
        self._base_llm_model = base_llm_model

    @property
    def llm_model(self):
        # Bind tools and enable structured output with the defined schema
        model_with_tools = self._base_llm_model.bind_tools([]).with_structured_output()
        return model_with_tools

    def __call__(self, data: List[dict]):
        # Define the system prompt
        prompt = """
        Context: You are an assistant helping teachers and instructors process their learning resources. 
        Your role is to analyze and extract data from various learning materials (lessons, 
        learning modules, assignments, exercises, etc.) of a specific course and convert it into a format suitable for 
        insertion into a graph database. This database will support a personalized learning resource 
        recommendation system tailored for students.

        Your main task is to categorize each learning resource and identify relevant concepts. For each 
        learning resource, you must identify and list at least 5 related concepts that represent the key 
        ideas or topics covered.

        Instructions:
        1. Carefully examine the provided JSON data and understand the main topics of the resource.
        2. Ensure each resource has at least 5 related concepts to maximize the utility of the recommendation system.
        3. Process each learning resource in the input data.

        Output your findings in the structured format defined by the schema.
        """

        # Prepare the messages for the LLM
        system_message = SystemMessage(prompt)
        human_message = HumanMessage(content=str(data))

        # Invoke the LLM with structured output
        structured_llm = self.llm_model
        for resource in data:
            llm_response = structured_llm.invoke([system_message, human_message])

            # Deserialize the structured response into the LearningResource schema
            try:
                learning_resource = llm_response

                # Add the resource to the graph database
                add_learning_resource(
                    resource_id=str(uuid4()),
                    llm_input=learning_resource.dict()
                )
                syslog.info(f"Successfully added learning resource: {learning_resource.resource_name}")

            except Exception as e:
                syslog.error(f"Failed to process resource: {resource}. Error: {e}")

    @Neo4jDBSessionProvider().inject_neo4j_async_session(argname="db_session")
    def add_learning_resource(
        self,
        db_session: Neo4jAsyncSession,
        course_id: str,
    ):
        pass
