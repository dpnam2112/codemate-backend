from typing import List
from core.response import Ok
from machine.models import *
from fastapi import APIRouter, Depends
from machine.schemas.requests import *
from machine.schemas.responses.recommend import *
from machine.controllers import *
from machine.providers import InternalProvider
from core.exceptions import NotFoundException, BadRequestException

router = APIRouter(prefix="/recommend_lessons", tags=["recomendation"])


@router.get("/{recommendLessonId}", response_model=Ok[RecommendLessonResponse])
async def recommend_lesson(
    recommendLessonId: UUID,
    recommend_lessons_controller: RecommendLessonsController = Depends(InternalProvider().get_recommendlessons_controller),
):
   
    # Fetch the lesson recommendation details
    recommend_lesson = await recommend_lessons_controller.recommend_lessons_repository.first(
        where_=[RecommendLessons.id == recommendLessonId],
        relations=[RecommendLessons.modules,  RecommendLessons.lesson],
    )

    if not recommend_lesson:
        raise NotFoundException(message="Recommend Lesson not found for the given ID.")

    lesson = recommend_lesson.lesson
    if not lesson:
        raise NotFoundException(message="Associated Lesson not found for the given Recommend Lesson.")

    response_data = RecommendLessonResponse(
        lesson_id=recommend_lesson.id,
        name=lesson.title,
        learning_outcomes=[outcome for outcome in lesson.learning_outcomes],
        description=lesson.description,
        progress=recommend_lesson.progress,
        status=recommend_lesson.status,
        recommend_content=recommend_lesson.recommended_content,
        explain=recommend_lesson.explain,
        modules=[
            ModuleResponse(
                module_id=module.id,
                title=module.title,
            )
            for module in recommend_lesson.modules
        ],
    )

    return Ok(data=response_data, message="Successfully fetched the recommended lesson.")