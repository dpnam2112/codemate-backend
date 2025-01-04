import uuid
from uuid import UUID
from datetime import datetime
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from machine.models.learning_paths import LearningPaths
from machine.services.workflows.lp_recommender import lp_recommender_workflow_factory
from machine.services.workflows.tools import lp_recommender_response
from machine.repositories.recommend_lessons import RecommendLessonsRepository
from machine.repositories.learning_paths import LearningPathsRepository
from core.db import Transactional


class AIRecommenderController:
    def __init__(
        self,
        recommend_lesson_repository: RecommendLessonsRepository,
        learning_paths_repository: LearningPathsRepository,
    ):
        """
        Initializes the AIRecommenderController.

        Args:
            recommend_lesson_repository (RecommendLessonsRepository): Repository for managing recommended lessons.
            learning_paths_repository (LearningPathsRepository): Repository for managing learning paths.
        """
        self.recommend_lesson_repository = recommend_lesson_repository
        self.learning_paths_repository = learning_paths_repository
        self.lp_recommender_agent = None

    async def __aenter__(self):
        """
        Asynchronous context manager entry. Initializes the learning path recommender agent.
        """
        self.lp_recommender_agent = lp_recommender_workflow_factory()

    async def __aexit__(self, exc_type, exc_value, traceback):
        """
        Asynchronous context manager exit. Cleans up the learning path recommender agent.

        Args:
            exc_type (type): Exception type (if any occurred during the context).
            exc_value (Exception): Exception instance (if any occurred during the context).
            traceback (traceback): Traceback object (if any exception occurred).
        """
        self.lp_recommender_agent = None

    async def _invoke_recommend_lesson_agent(
        self, user_id: UUID, course_id: UUID, goal: str
    ) -> lp_recommender_response:
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
        if not self.lp_recommender_agent:
            raise ValueError("lp_recommender_agent is not set.")

        lp_recommender_workflow = lp_recommender_workflow_factory()
        memory = MemorySaver()
        config = {"configurable": {"thread_id": "1", "course_id": str(course_id), "user_id": str(user_id)}}
        app = lp_recommender_workflow.compile(checkpointer=memory)

        final_state = app.invoke({"messages": [HumanMessage(content=goal)]}, config=config)
        tool_call = final_state["messages"][-1].tool_calls[0]
        args = tool_call["args"]

        return lp_recommender_response(**args)

    @Transactional()
    async def recommend_lessons(
        self, user_id: UUID, course_id: UUID, goal: str
    ) -> LearningPaths:
        """
        Generates personalized lesson recommendations, persists the data to the database, 
        and returns the new learning path instance.

        Args:
            user_id (UUID): Unique identifier of the user.
            course_id (UUID): Unique identifier of the course.
            goal (str): The learning goal specified by the user.

        Returns:
            LearningPaths: The new learning path instance.

        Raises:
            Exception: If there is an issue with persisting the data or invoking the agent.
        """
        # Invoke the agent to get recommendations
        response = await self._invoke_recommend_lesson_agent(user_id, course_id, goal)

        # Generate a new learning path
        learning_path_id = uuid.uuid4()
        new_learning_path = {
            "id": learning_path_id,
            "student_id": user_id,
            "course_id": course_id,
            "objective": goal,
            "start_date": datetime.now(),
        }
        learning_path_instance = await self.learning_paths_repository.create(new_learning_path)

        # Persist recommended lessons
        lesson_entries = [
            {
                "learning_path_id": learning_path_id,
                "lesson_id": item.id,  # Using the id from RecommenderItem as the lesson ID
                "explain": item.explanation,
                "status": "new",
            }
            for item in response.recommended_items
        ]
        await self.recommend_lesson_repository.create_many(lesson_entries)

        return learning_path_instance

