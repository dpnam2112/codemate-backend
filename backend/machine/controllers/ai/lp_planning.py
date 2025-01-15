from typing import Optional
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
    async def invoke_lp_planner(self, user_id: UUID, course_id: UUID, goal: Optional[str]) -> dict:
        """
        Generates personalized lesson recommendations, persists the data to the database, 
        and returns the new learning path instance.

        Args:
            user_id (UUID): Unique identifier of the user.
            course_id (UUID): Unique identifier of the course.
            goal (str): The learning goal specified by the user.

        Returns:
            dict: The new learning path instance.

        Raises:
            Exception: If there is an issue with persisting the data or invoking the agent.
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
        learning_path_instance = await self.learning_paths_repository.create(new_learning_path)

        # Step 3: Persist recommended lessons
        lesson_entries = [
            {
                "learning_path_id": str(learning_path_id),
                "lesson_id": item.id,  # From RecommendedLessonItem
                "explain": item.explanation,
                "status": "new",
            }
            for item in response.recommended_items
        ]
        await self.recommend_lesson_repository.create_many(lesson_entries)

        # Step 4: Persist learning modules
        for item in response.recommended_items:
            for module in item.modules:
                module_entry = {
                    "lesson_id": item.id,
                    "title": module.title,
                    "description": module.description,
                    "objectives": module.objectives,
                    "time_estimated": module.time_estimated,
                }
                await self.learning_paths_repository.create(module_entry)

        return learning_path_instance.to_dict()

