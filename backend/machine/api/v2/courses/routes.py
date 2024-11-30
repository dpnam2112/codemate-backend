from fastapi import APIRouter

from fastapi import APIRouter
from langchain_core.messages import HumanMessage
from machine.schemas.requests.v1.learning_resources import LearningResource
from machine.services.workflows.learning_resource_kg_builder import learning_resource_kg_builder
from langgraph.checkpoint.memory import MemorySaver
from machine.services.workflows import lp_recommender_workflow_factory
from machine.services.workflows.tools import get_learner_profile_and_learning_resources_tool, get_learner_profile_and_resource_related_concepts, lp_recommender_response
from core.logger import syslog

router = APIRouter(prefix="/courses", tags=["courses"])

@router.get("/")
async def get():
    pass

@router.post("/")
async def create(body: LearningResource):
    learning_resource_kg_builder(body.model_dump())

@router.post("{course_id}/recommend/{user_id}")
async def recommend(
    course_id: str,
    user_id: str
):
    lp_recommender_workflow = lp_recommender_workflow_factory()
    memory = MemorySaver()
    config = {"configurable": {"thread_id": "1", "course_id": course_id, "user_id": user_id}}
    app = lp_recommender_workflow.compile(checkpointer=memory)
    final_state = app.invoke({"messages": [HumanMessage(content="I want to become a backend developer.")]}, config=config)
    syslog.info("final_state =", final_state)

    tool_call = final_state["messages"][-1].tool_calls[0]
    syslog.info("tool_call =", tool_call)
    args = tool_call["args"]
    syslog.info("args =", args)
    return {"final_response": lp_recommender_response(**args).model_dump()["recommended_items"]}
