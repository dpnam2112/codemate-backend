from enum import StrEnum
from typing import Annotated, Sequence, TypedDict

from langchain_core.messages import BaseMessage, SystemMessage, ToolMessage

from machine.providers.ai_tool import AIToolProvider, LLMModelName
from machine.services.workflows.schemas import RecommenderItem
from .tools import get_learner_profile_and_learning_resources_tool, lp_recommender_response
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode
from core.logger import syslog
from langgraph.graph.message import add_messages

class NodeEnum(StrEnum):
    TOOL_NODE = "tool_node"
    LEARNING_RESOURCE_RECOMMENDER_NODE = "Learning resource recommender"

class AgentState(MessagesState):
    """The state of the agent."""

    # add_messages is a reducer
    # See https://langchain-ai.github.io/langgraph/concepts/low_level/#reducers
    final_response: lp_recommender_response

def workflow_router(state: MessagesState):
    messages = state['messages']

    last_message = messages[-1]

    syslog.info("last message =", last_message)
    if last_message.additional_kwargs.get("tool_calls"):
        tool_calls = last_message.additional_kwargs["tool_calls"]

        toolname = tool_calls[-1]["function"]["name"]
        print("tool=", tool_calls[-1])
        print("tool name=", tool_calls[-1]["function"]["name"])
        if toolname == "lp_recommender_response":
            return END

        return "tools"

    return END

def respond(state: AgentState):
    syslog.info("Invoke node 'respond'")
    print("response =", state["messages"][-1])
    tool_call = state["messages"][-1].tool_calls[0]
    syslog.info("tool_call =", tool_call)
    args = tool_call["args"]
    syslog.info("args =", args)
    return {"final_response": lp_recommender_response(**args).model_dump()["recommended_items"]}


def learning_resources_recommender_node(state: MessagesState):
    prompt = """
    You are a teacher assistant and your task is to give the learner's learning resources
    recommendations based on their profile. Here is how the process works:
    1. You will be received a learning goal.
    2. you **must** invoke the function 'get_learner_profile_and_learning_resources' with the list
    of analyzed concepts as arguments to retrieve all the learner's profile and learning resources
    that are best matched with him/her. There will be two things returned from the function:
        - Learner profile containing the numerical proficiency of the learner for each concept. For example:
        If the learner is very proficient as the concept 'Linked list', then the proficiency will be
        around 0.8 - 1.
        - If the learner hasn't learned the concept 'Binary Tree' before, then the proficiency will be 0.
        - If the learner has learned the concept 'Binary Tree', but still hasn't mastered it, then the
          proficiency may be in the range 0.3 - 0.7. The higher the score, the more proficient the
          learner is.
    3. Based on the user profile and learning resources, select the 5 learning resources that are
    the best to the learner and give them explanation why they have to learn those learning
    resources.Your explanation will help them know why they need to learn those learning resources, what they can achieve after
    interacting with those learning resources. Your explanation shouldn't contain any numeric
    information. For exmple, instead of saying to the learner like: "Your proficiency on the concept
    'Python Programming' is 0.7", you should say things like: "based on your profile, you are pretty
    good at Python programming...".
    Here is some example:
    - If the learner's proficiency on the concept 'Python programming' is 0.3, which means the
      learner is very weak at Python programming, and there is a learning resource covering that
      concept with the difficulty of 0.4, then you can explain to them like this:
      Based on your profile, your skill at Python programming is not good,...
      Your explanation must tell the user why she has to interact with that learning resource, which
      skills/concepts that she is weak at but the learning resource covers it with a reasonable
      difficulty. The explanation must be as detailed as possible. Also, your explanation must tell
      the user what skills they are weak at.
    4. After you complete, plug your analysis into the tool 'lp_recommender_response' and call it.
    Absolutely do not call this tool before you complete the above steps. Only call it at the final
    step.
    """

    syslog.info(f"Invoke node: 'recommender'")

    model = AIToolProvider().chat_model_factory(LLMModelName.GPT_4O_MINI)
    model_with_tools = model.bind_tools([get_learner_profile_and_learning_resources_tool, lp_recommender_response])

    system_message = SystemMessage(prompt)

    messages = state['messages']
    response = model_with_tools.invoke([system_message] + messages)

    return {"messages": [response]}

tool_node = ToolNode([get_learner_profile_and_learning_resources_tool, lp_recommender_response])

def lp_recommender_workflow_factory():
    workflow = StateGraph(MessagesState)

    workflow.add_node("recommender", learning_resources_recommender_node) 
    workflow.add_node("tools", tool_node)
    workflow.add_node("respond", respond)

    workflow.add_edge(START, "recommender")
    workflow.add_conditional_edges(
        "recommender",
        workflow_router,
        {"tools": "tools", "respond": "respond", END: END}
    )

    workflow.add_edge("tools", "recommender")
    workflow.add_edge("respond", END)
    return workflow
