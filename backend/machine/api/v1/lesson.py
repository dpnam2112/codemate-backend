from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from core.response import Ok
from machine.schemas.requests.lesson import PutLessonRequest, DeleteLessonRequest, ExerciseRequest, QuestionModel
from machine.schemas.responses.lesson import CreateNewLessonResponse, DocumentResponse, PutLessonResponse, DeleteLessonResponse, ExerciseResponse
from machine.providers import InternalProvider
from machine.controllers import *
from machine.models import *
from core.utils.file import upload_to_s3
from core.exceptions import NotFoundException, BadRequestException
from fastapi import FastAPI, File, UploadFile, Form
from uuid import UUID
from fastapi import File, Form, UploadFile, Depends
from typing import List
from core.settings import settings
from core.repository import SynchronizeSessionEnum
import uuid
router = APIRouter(prefix="/lessons", tags=["lesson"])
@router.post("/", response_model=Ok[CreateNewLessonResponse])
async def create_new_lesson(
    title: str = Form(...),
    description: str = Form(...),
    course_id: UUID = Form(...),
    order: int = Form(...),
    learning_outcomes: List[str] = Form(...),
    files: List[UploadFile] = File(None),
    lesson_controller: LessonsController = Depends(InternalProvider().get_lessons_controller),
    document_controller: DocumentsController = Depends(InternalProvider().get_documents_controller),
    course_controller: CoursesController = Depends(InternalProvider().get_courses_controller),
):
    """
    Creates a new lesson with optional documents.
    """
    # Check if the course exists
    course = await course_controller.courses_repository.first(
        where_=[Courses.id == course_id]
    )
    if not course:
        raise NotFoundException(message="Course not found for the given ID.")
    
    # Create a new lesson
    lesson_data = {
        "id": str(uuid.uuid4()),
        "title": title,
        "description": description,
        "course_id": course_id,
        "order": order,
        "learning_outcomes": learning_outcomes,
    }
    created_lesson = await lesson_controller.lessons_repository.create(
        lesson_data,
        commit=True,
        )

    documents = []
    if files:
        for file in files:
            if file.filename:
                # Upload file to S3
                content = await file.read()
                s3_key = await upload_to_s3(
                    file_content=content,
                    file_name=file.filename,
                    bucket_name=settings.AWS3_BUCKET_NAME,
                )

                # Save the document to the database
                document_data = {
                    "name": file.filename,
                    "type": file.content_type,
                    "document_url": s3_key,
                    "lesson_id": created_lesson.id,
                }
                created_document = await document_controller.documents_repository.create(
                    document_data,
                    commit=True,
                )
                documents.append(created_document)


    # Return the response
    return Ok(
        data= CreateNewLessonResponse(
            id=created_lesson.id,
            title=created_lesson.title,
            description=created_lesson.description,
            course_id=created_lesson.course_id,
            order=created_lesson.order,
            learning_outcomes=created_lesson.learning_outcomes,
            documents=[DocumentResponse(**doc.__dict__) for doc in documents],
        ),
        message="Successfully updated the lesson.",
    )
@router.put("/", response_model=Ok[PutLessonResponse])
async def update_lesson(
    put_lesson: PutLessonRequest,
    lesson_controller: LessonsController = Depends(InternalProvider().get_lessons_controller),
):
    """
    Updates an existing lesson.
    """
    lesson = await lesson_controller.lessons_repository.first(
        where_=[Lessons.id == put_lesson.lesson_id]
        )
    
    if not lesson:
        raise NotFoundException(message="Lesson not found for the given ID.")
    
    # Update the lesson
    lesson.learning_outcomes = put_lesson.learning_outcomes
    lesson.title = put_lesson.title
    lesson.description = put_lesson.description
    lesson.order = put_lesson.order
    
    # Save the updated lesson
    updated_lesson = await lesson_controller.lessons_repository.update(
        where_=[Lessons.id == put_lesson.lesson_id],
        attributes={
            "learning_outcomes": lesson.learning_outcomes,
            "title": lesson.title,
            "description": lesson.description,
            "order": lesson.order
        },
        commit=True,
    )

    return Ok(
        data= PutLessonResponse(
        lesson_id=updated_lesson.id,
        title=updated_lesson.title,
        description=updated_lesson.description,
        order=updated_lesson.order,
        learning_outcomes=updated_lesson.learning_outcomes
        ),
        message="Successfully updated the lesson.",
    )
@router.delete("/", response_model=Ok[DeleteLessonResponse])
async def delete_lesson(
    delete_lesson_request: DeleteLessonRequest,
    lesson_controller: LessonsController = Depends(InternalProvider().get_lessons_controller),
    recommend_lesson_controller: RecommendLessonsController = Depends(InternalProvider().get_recommendlessons_controller),
    document_controller: DocumentsController = Depends(InternalProvider().get_documents_controller),
):
    """
    Deletes a lesson by its ID, ensuring all related entities are also deleted.
    """
    # Fetch the lesson by ID with related entities
    lesson = await lesson_controller.lessons_repository.first(
        where_=[Lessons.id == delete_lesson_request.lesson_id],
        relations=[
            Lessons.documents,
            Lessons.student_lessons,
            Lessons.recommend_lesson,
        ],
    )
    
    if not lesson:
        raise NotFoundException(message="Lesson not found for the given ID.")

    # Delete related RecommendLessons
    if lesson.recommend_lesson:
        await recommend_lesson_controller.recommend_lessons_repository.delete(
            where_=[RecommendLessons.lesson_id == delete_lesson_request.lesson_id],
            synchronize_session=SynchronizeSessionEnum.FETCH,
        )

    # Delete related Documents
    if lesson.documents:
        await document_controller.documents_repository.delete(
            where_=[Documents.lesson_id == delete_lesson_request.lesson_id],
            synchronize_session=SynchronizeSessionEnum.FETCH,
        )

    # Delete the lesson itself
    deleted_lesson = await lesson_controller.lessons_repository.delete(
        where_=[Lessons.id == delete_lesson_request.lesson_id],
        synchronize_session=SynchronizeSessionEnum.FETCH,
    )
    # print(deleted_lesson)
    if not deleted_lesson:
        raise Exception("Failed to delete the lesson.")

    return Ok(
        data= DeleteLessonResponse(
        lesson_id=lesson.id,
        title=lesson.title,
        description=lesson.description,
        order=lesson.order,
        learning_outcomes=lesson.learning_outcomes,
        ),
        message="Successfully deleted the lesson.",
    )
@router.post("/documents", response_model=Ok[List[DocumentResponse]])
async def add_documents(
    lesson_id: UUID = Form(...),
    files: List[UploadFile] = File(...),
    document_controller: DocumentsController = Depends(InternalProvider().get_documents_controller),
):
    """
    Adds multiple documents to a specific lesson.
    """
    # Validate that files are provided
    if not files or all(file.filename == "" for file in files):
        raise ValueError("No files provided for upload.")

    documents = []

    for file in files:
        if file.filename:
            # Read file content
            content = await file.read()

            # Upload the file to S3
            s3_key = await upload_to_s3(
                file_content=content,
                file_name=file.filename,
                bucket_name=settings.AWS3_BUCKET_NAME,
            )

            # Save the document metadata to the database
            document_data = {
                "name": file.filename,
                "type": file.content_type,
                "document_url": s3_key,
                "lesson_id": lesson_id,
            }

            created_document = await document_controller.documents_repository.create(
                document_data, commit=True
            )

            documents.append(created_document)

    # Return the response
    return Ok(
        data=[DocumentResponse(**doc.__dict__) for doc in documents],
        message="Successfully added the documents.",
    )
@router.post("/exercises", response_model=Ok[ExerciseResponse])
async def add_exercises(
    body: ExerciseRequest,
    exercises_controller: ExercisesController = Depends(InternalProvider().get_exercises_controller),
    lesson_controller: LessonsController = Depends(InternalProvider().get_lessons_controller),
):
    """
    Adds a new exercise with questions to a lesson.
    """
    # Validate lesson existence
    lesson = await lesson_controller.lessons_repository.first(
        where_=[Lessons.id == body.lesson_id]
    )
    if not lesson:
        raise NotFoundException(message="Lesson not found for the given ID.")

    # Validate and process questions
    questions_data = []
    for question in body.questions:
        if not all([question.question, question.answer, question.options, question.type]):
            raise BadRequestException(
                message=f"Invalid question data: {question.model_dump()}. All fields must be provided.",
            )
        question_data = {
            **question.model_dump(),
            "type": question.type.value, 
        }
        questions_data.append(question_data)

    # Prepare exercise data
    exercise_data = {
        "name": body.name,
        "description": body.description,
        "deadline": body.deadline,
        "time": body.time,
        "topic": body.topic,
        "attempts": body.attempts,
        "difficulty": body.difficulty,
        "lesson_id": body.lesson_id,
        "questions": questions_data,
    }

    # Create the exercise
    created_exercise = await exercises_controller.exercises_repository.create(
        exercise_data, commit=True
    )

    # Return the response
    return Ok(
        data=ExerciseResponse(
            exercise_id=created_exercise.id,
            name=created_exercise.name,
            description=created_exercise.description,
            deadline=created_exercise.deadline,
            time=created_exercise.time,
            topic=created_exercise.topic,
            attempts=created_exercise.attempts,
            difficulty=created_exercise.difficulty,
            lesson_id=created_exercise.lesson_id,
            questions=[
                QuestionModel(
                    question=q["question"],
                    answer=q["answer"],
                    options=q["options"],
                    type=q["type"],
                    score=q["score"],
                ).model_dump()  # Convert to dictionary
                for q in exercise_data["questions"]
            ],
        ),
        message="Successfully created the exercise.",
    )
@router.put("/exercises/{exercise_id}", response_model=Ok[ExerciseResponse])
async def update_exercise(
    exercise_id: UUID,
    body: ExerciseResponse,
    exercises_controller: ExercisesController = Depends(InternalProvider().get_exercises_controller),
    lesson_controller: LessonsController = Depends(InternalProvider().get_lessons_controller),
):
    """
    Updates an existing exercise with new details and questions.

    """
    # Validate exercise existence
    exercise = await exercises_controller.exercises_repository.first(
        where_=[Exercises.id == exercise_id]
    )
    if not exercise:
        raise NotFoundException(message="Exercise not found for the given ID.")

    # Validate lesson existence
    lesson = await lesson_controller.lessons_repository.first(
        where_=[Lessons.id == body.lesson_id]
    )
    if not lesson:
        raise NotFoundException(message="Lesson not found for the given ID.")

    # Validate and process questions
    questions_data = []
    for question in body.questions:
        if not all([question.question, question.answer, question.options, question.type]):
            raise BadRequestException(
                message=f"Invalid question data: {question.model_dump()}. All fields must be provided.",
            )
        question_data = {
            **question.model_dump(),
            "type": question.type.value,  # Convert enum to string
        }
        questions_data.append(question_data)

    # Prepare updated exercise data
    exercise.name = body.name
    exercise.description = body.description
    exercise.deadline = body.deadline
    exercise.time = body.time
    exercise.topic = body.topic
    exercise.attempts = body.attempts
    exercise.difficulty = body.difficulty
    exercise.lesson_id = body.lesson_id
    exercise.questions = questions_data

    # Update the exercise
    updated_exercise = await exercises_controller.exercises_repository.update(
        where_=[Exercises.id == exercise_id],
        attributes={
            "name": exercise.name,
            "description": exercise.description,
            "deadline": exercise.deadline,
            "time": exercise.time,
            "topic": exercise.topic,
            "attempts": exercise.attempts,
            "difficulty": exercise.difficulty,
            "lesson_id": exercise.lesson_id,
            "questions": exercise.questions,
        },
        commit=True,
    )

    # Return the response
    return Ok(
        data=ExerciseResponse(
            exercise_id=updated_exercise.id,
            name=updated_exercise.name,
            description=updated_exercise.description,
            deadline=updated_exercise.deadline,
            time=updated_exercise.time,
            topic=updated_exercise.topic,
            attempts=updated_exercise.attempts,
            difficulty=updated_exercise.difficulty,
            lesson_id=updated_exercise.lesson_id,
            questions=[
                QuestionModel(
                    question=q["question"],
                    answer=q["answer"],
                    options=q["options"],
                    type=q["type"],
                    score=q["score"],
                ).model_dump()  # Convert to dictionary
                for q in updated_exercise.questions
            ],
        ),
        message="Successfully updated the exercise.",
    )
