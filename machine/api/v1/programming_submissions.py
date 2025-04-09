from fastapi.security import OAuth2
from core.response.api_response import Ok, PaginationResponse
from core.utils.auth_utils import verify_token
from machine.models import *
from fastapi import APIRouter, Depends
from machine.schemas.programming_submission import ProgrammingSubmissionSchema, ProgrammingSubmissionStatSchema
from machine.schemas.requests import *
from machine.schemas.responses.recommend import *
from machine.schemas.responses.quiz import *
from machine.schemas.responses.document import *
from machine.controllers import *
from machine.providers import InternalProvider
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
router = APIRouter(prefix="/programming-submissions", tags=["Programming submissions"])

@router.get("/{submission_id}")
async def get_submission_details(
    submission_id: UUID,
    exercise_controller: ExercisesController = Depends(InternalProvider().get_exercises_controller)
):
    submission = await exercise_controller.get_submission(submission_id)
    return Ok(data=ProgrammingSubmissionSchema.model_validate(submission))

@router.get("", response_model=PaginationResponse[ProgrammingSubmissionStatSchema])
async def get_submissions_with_stat(
    exercise_id: UUID,
    token: str = Depends(oauth2_scheme),
    exercise_controller: ExercisesController = Depends(InternalProvider().get_exercises_controller)
):
    user_id = verify_token(token).get("sub")
    submission_with_stat = await exercise_controller.list_submissions_with_stats(user_id, exercise_id)

    response_data = []
    for item in submission_with_stat:
        data = {
            **item["submission"].to_dict(), "passed_testcases": item["passed_testcases"], "total_testcases": item["total_testcases"]
        }
        response_data.append(ProgrammingSubmissionStatSchema.model_validate(data))
    return PaginationResponse(
        data=response_data,
        total=len(submission_with_stat)
    )
