from typing import List
from core.response import Ok
from machine.models import *
from fastapi import APIRouter, Depends
from machine.schemas.requests import *
from machine.schemas.responses.recommend import *
from machine.controllers import *
from machine.providers import InternalProvider
from core.utils.auth_utils import verify_token
from machine.schemas.responses.courses import *
from fastapi.security import OAuth2PasswordBearer
from core.exceptions import NotFoundException, BadRequestException

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
router = APIRouter(prefix="/recommend_lessons", tags=["recommendation"])


@router.get("/{recommendLessonId}", response_model=Ok[RecommendLessonResponse])
async def recommend_lesson(
    recommendLessonId: UUID,
    token : str = Depends(oauth2_scheme),
    student_controller: StudentController = Depends(InternalProvider().get_student_controller),
    recommend_lessons_controller: RecommendLessonsController = Depends(InternalProvider().get_recommendlessons_controller),
):
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")
    user = await student_controller.student_repository.first(where_=[Student.id == user_id])
    if not user:
        raise NotFoundException(message="Only Student have the permission to get this recommend lesson.")
    # Fetch the lesson recommendation details
    recommend_lesson = await recommend_lessons_controller.recommend_lessons_repository.first(
        where_=[RecommendLessons.id == recommendLessonId],
        relations=[RecommendLessons.modules,  RecommendLessons.lesson, RecommendLessons.learning_path],
    )

    if not recommend_lesson:
        raise NotFoundException(message="Recommend Lesson not found for the given ID.")

    if not recommend_lesson.learning_path.student_id == user.id:
        raise NotFoundException(message="You are not authorized to access this recommend lesson.")
    
    lesson = recommend_lesson.lesson
    if not lesson:
        raise NotFoundException(message="Associated Lesson not found for the given Recommend Lesson.")
    
    get_modules = recommend_lesson.modules
    if not get_modules:
        raise NotFoundException(message="Modules not found for the given Recommend Lesson.")

    response_data = RecommendLessonResponse(
        lesson_id=recommend_lesson.id,
        name=lesson.title,
        learning_outcomes=[outcome for outcome in lesson.learning_outcomes],
        description=lesson.description,
        progress=recommend_lesson.progress,
        status=recommend_lesson.status,
        recommend_content=recommend_lesson.recommended_content,
        explain=recommend_lesson.explain,
        start_date=recommend_lesson.start_date,
        end_date=recommend_lesson.end_date,
        duration_notes=recommend_lesson.duration_notes,
        modules=[
            ModuleResponse(
                module_id=module.id,
                title=module.title,
                progress=module.progress,
                objectives=[objective for objective in module.objectives],
            )
            for module in get_modules
        ],
    )

    return Ok(data=response_data, message="Successfully fetched the recommended lesson.")

@router.get("/{recommendLessonId}/bookmark")
async def bookmark_recommend_lesson(
    recommendLessonId: str,
    token: str = Depends(oauth2_scheme),
    recommend_lessons_controller: RecommendLessonsController = Depends(InternalProvider().get_recommendlessons_controller),
    student_controller: StudentController = Depends(InternalProvider().get_student_controller),
):
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")
    
    check_student_role = await student_controller.student_repository.first(
        where_=[Student.id == user_id],
    )
    
    if not check_student_role:
        raise NotFoundException(message="You are not a student. Please log in as a student to access this feature.")

    # Fetch the lesson recommendation details
    recommend_lesson = await recommend_lessons_controller.recommend_lessons_repository.first(
        where_=[RecommendLessons.id == recommendLessonId]
    )

    if not recommend_lesson:
        raise NotFoundException(message="Recommend Lesson not found for the given ID.")
    
    update_bookmark = not recommend_lesson.bookmark
    print(f"Bookmark status before update: {recommend_lesson.bookmark}")
    print(f"Bookmark status after update: {update_bookmark}")
    updated_recommend_lesson = await recommend_lessons_controller.recommend_lessons_repository.update(
        where_=[RecommendLessons.id == recommendLessonId],
        attributes={
            "bookmark": update_bookmark,
        },
        commit=True,
    )
    
    if not updated_recommend_lesson:
        raise NotFoundException(message="Bookmark not found for the given Recommend Lesson.")
    
    # Create a Pydantic model or dict representation instead of returning the SQLAlchemy model directly
    result = {
        "id": str(updated_recommend_lesson.id),
        "lesson_id": str(updated_recommend_lesson.lesson_id) if updated_recommend_lesson.lesson_id else None,
        "bookmark": updated_recommend_lesson.bookmark,
    }
    
    return Ok(data=result, message="Successfully toggled the bookmark status of the recommended lesson.")