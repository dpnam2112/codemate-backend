from uuid import uuid4

from langchain_core.messages import HumanMessage, SystemMessage

from machine.providers.ai_tool import AIToolProvider
from core.logger import syslog
from machine.services.workflows.schemas import AddLearningResource
from .tools import add_learning_resource

def learning_resource_kg_builder(data: dict):
    prompt = """
    Context: You are an assistant helping teachers and instructors process their learning resources. 
    Your role is to analyze and extract data from various learning materials (such as courses, lessons, 
    learning modules, assignments, exercises, etc.) and convert it into a format suitable for 
    insertion into a graph database. This database will support a personalized learning resource 
    recommendation system tailored for students.

    Your main task is to use the tool `AddLearningResource` to categorize each learning resource 
    and identify relevant concepts. For each learning resource, you must identify and list at least 
    5 related concepts that represent the key ideas or topics covered.

    Instructions:
    1. Carefully examine the provided JSON data and understand the main topics of the resource.
    2. Use `add_learning_resource` to log the resource details and associated concepts.
    3. Ensure each resource has at least 5 related concepts to maximize the utility of the recommendation system.
    4. If the input data is a JSON array, please call AddLearningResource function for each learning
    resource in the array.

    Output your findings in a structured format.
    """

    model = AIToolProvider().chat_model_factory()
    model_with_tools = model.bind_tools([AddLearningResource], tool_choice="AddLearningResource")
    system_message = SystemMessage(prompt)
    human_message = HumanMessage(str(data))
    llm_response = model_with_tools.invoke([system_message, human_message])
    tool_calls = llm_response.model_dump()["tool_calls"]
    for llm_call, data_ in zip(tool_calls, data):
        if llm_call['name'] == 'AddLearningResource':
            llm_input = AddLearningResource(**llm_call["args"])
            add_learning_resource(str(uuid4()), llm_input=llm_input)
            syslog.info("Successfully added learning resource: ", data)
