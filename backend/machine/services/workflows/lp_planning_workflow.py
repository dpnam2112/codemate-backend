from langchain_core.messages import SystemMessage
from .ai_tool_provider import AIToolProvider, LLMModelName
from .tools import LPPlanningWorkflowResponse, get_learner_profile, get_related_lessons
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode
from core.logger import syslog

class AgentState(MessagesState):
    """The state of the agent."""

    # add_messages is a reducer
    # See https://langchain-ai.github.io/langgraph/concepts/low_level/#reducers
    final_response: LPPlanningWorkflowResponse

tools = [get_learner_profile, LPPlanningWorkflowResponse, get_related_lessons]

def workflow_router(state: MessagesState):
    messages = state['messages']

    last_message = messages[-1]
    if last_message.additional_kwargs.get("tool_calls"):
        tool_calls = last_message.additional_kwargs["tool_calls"]

        toolname = tool_calls[-1]["function"]["name"]
        if toolname == "LPPlanningWorkflowResponse":
            return END

        return "tools"

    return END

def respond(state: AgentState):
    syslog.info("Invoke node 'respond'")
    tool_call = state["messages"][-1].tool_calls[0]
    args = tool_call["args"]
    return LPPlanningWorkflowResponse(**args)


def lp_planning_agent(state: MessagesState):
    prompt = """
    You are a teaching assistant for a course and your task is to give the learner lesson
    recommendations, and additionally, design learning content for each lesson, based on their
    profile. The structure of the course is designed by lecturers/teachers, but they need you to
    design the structure/content for each lesson so that it is suitable for each student. Students
    may give you a learning goal for the course, so that your learning content design should
    be also suitable with their learning goals. Here is how the process work:

    1. You will be received a learning goal (Optional).

    2. Retrieve learner profile. The learner profile contains basic information about the
    learner as well as a proficiency vector, which is a mapping from concepts to the learner's
    proficiency/mastery of the concept. The learner profile must include **all** proficiency of the
    learner of the concepts that the course covers.

        - Learner profile containing the numerical proficiency of the learner for each concept. For example:
        If the learner is very proficient as the concept 'Linked list', then the proficiency will be
        around 0.8 - 1.

        - If the learner hasn't learned the concept 'Binary Tree' before, then the proficiency will be 0.

        - If the learner has learned the concept 'Binary Tree', but still hasn't mastered it, then the
          proficiency may be in the range 0.3 - 0.7. The higher the score, the more proficient the
          learner is.

    3. Retrieve all related lessons of the course. The returned data include information of each
    lesson, as well as difficulty vector for each lesson. A difficulty vector is a mapping from
    concepts to difficulty values, which range from 0 to 1. The higher difficulty value is, the more
    difficult the lesson is on that specific concept. You must retrieve **all** lessons related to
    the course.

    4. Based on the user profile and lessons retrieved in the previous steps, give the learner
    explanation why they have to learn those lessons. Remember Goal-Setting theory, which tells us
    that clear, challenging goals improve motivation and performance?  Your explaination will help
    them to know why they should learn that lesson, and how those lessons can help them achieve
    their goals. Your explanation must be based on the learner profile and the lessons.

    5. Now it's our time to design an appropriate learning path for our students! From
    the lesson's id, fetch the lesson's related data like: learning outcomes/lesson outcomes,
    lesson's content description (If there is any that doesn't have). From these information. You
    have to design modules for each lesson. For each module, you have to determine:
    - Objectives: objectives of the module.
    - Title: Title of the module. Description: description of the module, what the module will teach the learner. Time: estimated time that the user need to complete the module, based on their current mastery of the concepts. 6. After completing all 4 steps, you must invoke the tool: `LPPlanningWorkflowResponse` to return the output to the caller so that it can use your output in the next steps (e.g: return the output to the user).

    Rules:
    - Only use tools `get_learner_profile` and `get_related_lessons` only once to save resources. Do
      not make multiple calls.
    """

    model = AIToolProvider().chat_model_factory(LLMModelName.GPT_4O_MINI)
    model_with_tools = model.bind_tools(tools)

    system_message = SystemMessage(prompt)

    messages = state['messages']
    response = model_with_tools.invoke([system_message] + messages)
    syslog.debug("response =", response)

    return {"messages": [response]}


tool_node = ToolNode(tools)

def lp_planning_workflow_factory():
    workflow = StateGraph(MessagesState)

    workflow.add_node("lp_planning_agent", lp_planning_agent) 
    workflow.add_node("tools", tool_node)
    workflow.add_node("respond", respond)

    workflow.add_edge(START, "lp_planning_agent")
    workflow.add_conditional_edges(
        "lp_planning_agent",
        workflow_router,
        {"tools": "tools", "respond": "respond", END: END}
    )

    workflow.add_edge("tools", "lp_planning_agent")
    workflow.add_edge("respond", END)
    return workflow
