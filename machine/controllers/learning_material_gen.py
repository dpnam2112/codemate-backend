from core.db import Transactional
from uuid import UUID
from core.repository.enum import ExerciseType
import machine.repositories as repos
import machine.services as services
import machine.models as models

class LearningMaterialGenController:
    def __init__(
        self,
        module_repo: repos.ModulesRepository,
        exercises_repo: repos.ExercisesRepository,
        pl_config_repo: repos.ProgrammingLanguageConfigRepository,
        testcase_repo: repos.ProgrammingTestCaseRepository,
        programming_exercise_service: services.ProgrammingExerciseGenService
    ):
        """
        Initialize the controller with the specified repositories and services.

        :param module_repo: Repository for managing modules.
        :param exercises_repo: Repository for managing exercises.
        :param pl_config_repo: Repository for managing programming language configurations.
        :param testcase_repo: Repository for managing programming test cases.
        :param programming_exercise_service: Service for generating programming exercises.
        """
        self.module_repo = module_repo
        self.exercises_repo = exercises_repo
        self.programming_exercise_service = programming_exercise_service
        self.pl_config_repo = pl_config_repo
        self.testcase_repo = testcase_repo
    
    @Transactional()
    async def generate_programming_exercise(self, module_id: UUID):
        module = await self.module_repo.first(where_=[models.Modules.id == module_id])
        if not module:
            raise ValueError("Module not found.")

#        # 🔍 Check for existing generated coding exercise
#        existing_exercise = await self.exercises_repo.first(
#            where_=[
#                models.Exercises.id == module.id,
#                models.Exercises.source == "generated_by_ai",
#                models.Exercises.type == ExerciseType.code
#            ],
#        )
#
#        if existing_exercise:
#            return existing_exercise

        # 🧠 Generate new coding exercise using AI
        result = await self.programming_exercise_service.generate_programming_exercise(
            module_title=module.title,
            objectives=module.objectives,
        )

        # 💾 Save exercise
        exercise_data = {
            "name": result.name,
            "description": result.problem_description,
            "type": ExerciseType.code,
            "questions": [],
            "source": "generated_by_ai",
            "module_id": module.id,
            "grading_method": "highest",
            "attempts_allowed": 1
        }
        exercise = await self.exercises_repo.create(exercise_data, commit=True)

        # 💾 Save testcases
        testcases = [
            {
                "exercise_id": exercise.id,
                "input": tc.input,
                "expected_output": tc.expected_output,
                "is_public": True,
                "score": 1.0
            }
            for tc in result.test_cases
        ]
        await self.testcase_repo.create_many(testcases)

        # 💾 Save language configs
        language_configs = [
            {
                "exercise_id": exercise.id,
                "judge0_language_id": boilerplate_code.judge0_lang_id,
                "boilerplate_code": boilerplate_code.code,
                "time_limit": 0,
                "memory_limit": 0
            }
            for boilerplate_code in result.boilerplate_codes
        ]
        await self.pl_config_repo.create_many(language_configs)

        return exercise


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
        pg_lang_config_repo = repos.ProgrammingLanguageConfigRepository(
            model=models.ProgrammingLanguageConfig, db_session=session
        )
        programming_exercise_repo = repos.ExercisesRepository(model=models.Exercises, db_session=session)
        testcase_repo = repos.ProgrammingTestCaseRepository(db_session=session)
        
        controller = LearningMaterialGenController(
            module_repo, programming_exercise_repo, pg_lang_config_repo, testcase_repo,programming_exercise_service
        )

        # Example UUID for testing
        module_id = UUID("9ddb52d7-5a82-4115-91c9-7255aaad2b04")
        
        # Generate programming exercise
        programming_exercise = await controller.generate_programming_exercise(module_id)
        print(programming_exercise.id)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
