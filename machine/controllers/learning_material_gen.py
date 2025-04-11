from core.db import Transactional
from uuid import UUID
import machine.repositories as repos
import machine.services as services
import machine.models as models

class LearningMaterialGenController:
    def __init__(
        self,
        module_repo: repos.ModulesRepository,
        programming_exercise_service: services.ProgrammingExerciseGenService
    ):
        """
        Initialize the controller with the specified repositories and services.

        :param module_repo: Repository for managing modules.
        :param programming_exercise_service: Service for generating programming exercises.
        """
        self.module_repo = module_repo
        self.programming_exercise_service = programming_exercise_service
    
    @Transactional()
    async def get_or_generate_programming_exercise(self, module_id: UUID):
        module = await self.module_repo.first(
            where_=[models.Modules.id == module_id],
        )

        programming_exercise = await self.programming_exercise_service.generate_programming_exercise(
            module_title=module.title,
            objectives=module.objectives,
        )

        return programming_exercise

import asyncio
from uuid import UUID
from machine.models import Exercises, ProgrammingSubmission
from machine.repositories import ExercisesRepository
from machine.repositories.programming_submission import ProgrammingSubmissionRepository
from core.db.session import DB_MANAGER, Dialect
from core.db.utils import session_context

async def main():
    async with session_context(DB_MANAGER[Dialect.POSTGRES]) as session:
        module_repo = repos.ModulesRepository(model=models.Modules, db_session=session)
        programming_exercise_service = services.ProgrammingExerciseGenService()
        
        controller = LearningMaterialGenController(module_repo, programming_exercise_service)

        # Example UUID for testing
        module_id = UUID("9ddb52d7-5a82-4115-91c9-7255aaad2b04")
        
        # Generate programming exercise
        programming_exercise = await controller.get_or_generate_programming_exercise(module_id)
        
        print(programming_exercise)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
