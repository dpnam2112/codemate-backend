from enum import StrEnum
from typing import Annotated, Literal, Sequence, TypedDict, Union

from langchain_core.messages import BaseMessage, SystemMessage

from machine.providers.ai_tool import AIToolProvider
from .tools import get_learner_profile_and_learning_resources
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode
from core.logger import syslog
from langgraph.graph.message import add_messages

class NodeEnum(StrEnum):
    TOOL_NODE = "tool_node"
    LEARNING_RESOURCE_RECOMMENDER_NODE = "Learning resource recommender"

class AgentState(TypedDict):
    """The state of the agent."""

    # add_messages is a reducer
    # See https://langchain-ai.github.io/langgraph/concepts/low_level/#reducers
    messages: Annotated[Sequence[BaseMessage], add_messages]

def workflow_router(state: MessagesState):
    messages = state['messages']

    last_message = messages[-1]

    syslog.info("last message =", last_message)

    if last_message.tool_calls:
        return "tools"

    return END

def learning_resources_recommender_node(state: MessagesState):
    prompt = """
    You are a teacher assistant and your task is to give the learner's learning resources
    recommendations based on their profile. Here is how the process works:
    1. You will be received a learning goal.
    2. From the learning goals, you have to analyze all concepts related to the learning goals that
    the learner has to master to reach his/her goal. Your list of concepts have to be ranked from
    easy to hard. Don't just analyze hard concepts and ignore easy concepts and vice versa. The
    number of concepts must be at least 20.
    3. After analyzing the necessary concepts, you **must** invoke the function
    'get_learner_profile_and_learning_resources' with the list of analyzed concepts as arguments to
    retrieve all the learner's profile and learning resources that are best matched with him/her.
    4. Based on the user profile and learning resources, select the 5 learning resources that are
    the best to the learner and give them explanation why they have to learn those learning
    resources, starting explaining their strong points and weak points. Your explanation will help
    them know why they need to learn those learning resources, what they can achieve after
    interacting with those learning resources. Your explanation shouldn't contain any numeric
    information. For exmple, instead of saying to the learner like: "Your proficiency on the concept
    'Python Programming' is 0.7", you should say things like: "based on your profile, you are pretty
    good at Python programming...". Also,  give them a reference to the learning resource, the
    reference may be a learning resource code retrieved from the tool, or a link to the learning
    resoure if it exists. A link must be preferred.
    """

    syslog.info(f"Invoke node: 'recommender'")

    model = AIToolProvider().chat_model_factory()
    model_with_tools = model.bind_tools([get_learner_profile_and_learning_resources])

    system_message = SystemMessage(prompt)

    messages = state['messages']
    response = model_with_tools.invoke([system_message] + messages)

    return {"messages": [response]}

tool_node = ToolNode([get_learner_profile_and_learning_resources])

def lp_recommender_workflow_factory():
    workflow = StateGraph(MessagesState)

    workflow.add_node("recommender", learning_resources_recommender_node) 
    workflow.add_node("tools", tool_node)

    workflow.add_edge(START, "recommender")
    workflow.add_edge("recommender", "tools")
    workflow.add_conditional_edges("recommender", workflow_router, {"tools": "tools", END: END})
    workflow.add_edge("tools", "recommender")

    return workflow
