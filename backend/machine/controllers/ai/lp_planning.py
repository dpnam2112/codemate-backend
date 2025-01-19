from typing import Any, Optional
from uuid import UUID, uuid4
from datetime import datetime
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from machine.repositories.modules import ModulesRepository
from machine.services.workflows.lp_planning_workflow import lp_planning_workflow_factory
from machine.services.workflows.tools import LPPlanningWorkflowResponse
from machine.repositories.recommend_lessons import RecommendLessonsRepository
from machine.repositories.learning_paths import LearningPathsRepository
from core.db import Transactional


class LPPPlanningController:
    def __init__(
        self,
        recommend_lesson_repository: RecommendLessonsRepository,
        module_repository: ModulesRepository,
        learning_paths_repository: LearningPathsRepository,
    ):
        self.recommend_lesson_repository = recommend_lesson_repository
        self.learning_paths_repository = learning_paths_repository
        self.module_repository = module_repository
        self.lp_planner_agent = None

    async def __aenter__(self):
        """
        Asynchronous context manager entry. Initializes the learning path planner agent.
        """
        self.lp_planner_agent = lp_planning_workflow_factory()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        """
        Asynchronous context manager exit. Cleans up the learning path planner agent.

        Args:
            exc_type (type): Exception type (if any occurred during the context).
            exc_value (Exception): Exception instance (if any occurred during the context).
            traceback (traceback): Traceback object (if any exception occurred).
        """
        self.lp_planner_agent = None

    async def _invoke_lesson_planning_workflow(
        self, user_id: UUID, course_id: UUID, goal: Optional[str]
    ):
        """
        Invokes the recommendation workflow to generate personalized learning recommendations.

        Args:
            user_id (UUID): Unique identifier for the user.
            course_id (UUID): Unique identifier for the course.
            goal (str): Learning goal provided by the user.

        Returns:
            lp_recommender_response: Recommendations and their explanations.

        Raises:
            ValueError: If the recommendation agent is not initialized properly.
        """
        if not self.lp_planner_agent:
            raise ValueError("lp_planner_agent is not set.")

        lp_planner_workflow = lp_planning_workflow_factory()
        memory = MemorySaver()
        config = {"configurable": {"thread_id": "1", "course_id": str(course_id), "user_id": str(user_id)}}
        app = lp_planner_workflow.compile(checkpointer=memory)

        final_state = app.invoke({"messages": [HumanMessage(content=goal)]}, config=config)
        tool_call = final_state["messages"][-1].tool_calls[0]
        args = tool_call["args"]

        return LPPlanningWorkflowResponse(**args)

    @Transactional()
    async def invoke_lp_planner(self, user_id: UUID, course_id: UUID, goal: Optional[str]) -> tuple[dict, LPPlanningWorkflowResponse]:
        """
        Generates personalized lesson recommendations, persists the data to the database, 
        and returns the new learning path instance along with the agent's response.

        Args:
            user_id (UUID): Unique identifier of the user initiating the request.
            course_id (UUID): Unique identifier of the course for which the learning path is being planned.
            goal (Optional[str]): A specific learning goal provided by the user to guide the recommendation.

        Returns:
            tuple[dict, LPPlanningWorkflowResponse]:
                - dict: A dictionary representation of the newly created learning path instance, including its ID, student ID, course ID, objective, and start date.
                - LPPlanningWorkflowResponse: The detailed response from the learning path planning workflow, including recommended lessons and modules.

        Raises:
            Exception: If an error occurs during the recommendation process or while persisting data to the database.
        """
        # Step 1: Invoke the agent to get recommendations
        response = await self._invoke_lesson_planning_workflow(user_id, course_id, goal)

        # Step 2: Create a new learning path instance
        learning_path_id = uuid4()
        new_learning_path = {
            "id": str(learning_path_id),
            "student_id": str(user_id),
            "course_id": str(course_id),
            "objective": goal,
            "start_date": datetime.now()
        }
        learning_path_instance = await self.learning_paths_repository.create(new_learning_path, commit=False)

        # Step 3: Persist recommended lessons and generate UUIDs
        recommend_lesson_entries = []
        lesson_uuid_map = {}  # Map to store recommend_lesson_id for each lesson

        for item in response.recommended_items:
            recommend_lesson_id = uuid4()  # Generate a UUID for the recommend lesson
            lesson_uuid_map[item.id] = recommend_lesson_id  # Map original lesson id to the new UUID

            recommend_lesson_entries.append({
                "id": str(recommend_lesson_id),  # New UUID for recommend_lesson
                "learning_path_id": str(learning_path_id),
                "lesson_id": item.id,  # Original lesson id
                "explain": item.explanation,
                "status": "new",
            })

        await self.recommend_lesson_repository.create_many(recommend_lesson_entries, commit=False)

        # Step 4: Persist learning modules
        module_entries = []

        for item in response.recommended_items:
            recommend_lesson_id = lesson_uuid_map[item.id]  # Get the mapped recommend_lesson_id
            for module in item.modules:
                module_entries.append({
                    "id": str(uuid4()),  # Generate UUID for the module
                    "recommend_lesson_id": str(recommend_lesson_id),  # Foreign key to recommend_lesson
                    "title": module.title,
                    "objectives": module.objectives
                })

        await self.module_repository.create_many(module_entries, commit=False)

        return learning_path_instance.to_dict(), response
