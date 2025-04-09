from core.response.api_response import Ok
from machine.models import *
from fastapi import APIRouter, Depends
from machine.schemas.programming_submission import ProgrammingSubmissionSchema
from machine.schemas.requests import *
from machine.schemas.responses.recommend import *
from machine.schemas.responses.quiz import *
from machine.schemas.responses.document import *
from machine.controllers import *
from machine.providers import InternalProvider

router = APIRouter(prefix="/programming-submissions", tags=["Programming submissions"])

@router.get("/{submission_id}")
async def get_submission_details(
    submission_id: UUID,
    exercise_controller: ExercisesController = Depends(InternalProvider().get_exercises_controller)
):
    submission = await exercise_controller.get_submission(submission_id)
    return Ok(data=ProgrammingSubmissionSchema.model_validate(submission))
