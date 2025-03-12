from typing import List
from fastapi import APIRouter, Depends
from core.response import Ok

from machine.schemas.responses.lesson import (
    CreateNewLessonResponse,
    DocumentResponse,
    PutLessonResponse,
    DeleteLessonResponse,
    GetDocumentResponse
)
from machine.providers import InternalProvider
from machine.controllers import *
from machine.models import *
from core.utils.file import upload_to_s3
from core.exceptions import NotFoundException, BadRequestException
from fastapi import File, UploadFile, Form
from uuid import UUID
from fastapi import File, Form, UploadFile, Depends
from core.settings import settings
from core.repository import SynchronizeSessionEnum
import uuid
from fastapi.security import OAuth2PasswordBearer
from core.utils.auth_utils import verify_token
from core.utils.file import generate_presigned_url
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
router = APIRouter(prefix="/lessons", tags=["lesson"])


@router.post("/", response_model=Ok[CreateNewLessonResponse])
async def create_new_lesson(
    title: str = Form(...),
    description: str = Form(...),
    course_id: UUID = Form(...),
    order: int = Form(...),
    learning_outcomes: List[str] = Form(...),
    files: List[UploadFile] = File(None),
    description_file: List[str] = Form(None),
    token: str = Depends(oauth2_scheme),
    lesson_controller: LessonsController = Depends(InternalProvider().get_lessons_controller),
    document_controller: DocumentsController = Depends(InternalProvider().get_documents_controller),
    course_controller: CoursesController = Depends(InternalProvider().get_courses_controller),
    professor_controller: ProfessorController = Depends(InternalProvider().get_professor_controller),
):
    """
    Creates a new lesson with optional documents and descriptions.
    """
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")

    user = await professor_controller.professor_repository.first(where_=[Professor.id == user_id])
    if not user:
        raise NotFoundException(message="Only professors have the permission to create lesson.")

    course = await course_controller.courses_repository.first(where_=[Courses.id == course_id])
    if not course:
        raise NotFoundException(message="Course not found for the given ID.")

    if user.id != course.professor_id:
        raise BadRequestException(message="You are not allowed to create a lesson in this course.")

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
        if description_file and len(files) != len(description_file):
            raise BadRequestException(message="Number of descriptions must match number of files.")

        for file, desc in zip(files, description_file or []):
            if file.filename:
                content = await file.read()

                s3_key = await upload_to_s3(
                    file_content=content,
                    file_name=file.filename,
                )
                
                document_data = {
                    "name": file.filename,
                    "type": file.content_type,
                    "document_url": s3_key,
                    "description": desc,
                    "lesson_id": created_lesson.id,
                }
                created_document = await document_controller.documents_repository.create(
                    document_data,
                    commit=True,
                )
                documents.append(created_document)

    return Ok(
        data=CreateNewLessonResponse(
            id=created_lesson.id,
            title=created_lesson.title,
            description=created_lesson.description,
            course_id=created_lesson.course_id,
            order=created_lesson.order,
            learning_outcomes=created_lesson.learning_outcomes,
            documents=[DocumentResponse(**doc.__dict__) for doc in documents],
        ),
        message="Successfully created the lesson.",
    )


@router.put("/", response_model=Ok[PutLessonResponse])
async def update_lesson(
    lesson_id: UUID = Form(...),
    title: str = Form(...),
    description: str = Form(...),
    order: int = Form(...),
    learning_outcomes: List[str] = Form(...),
    # files: List[UploadFile] = File(None),
    # description_file: List[str] = Form(None),
    token: str = Depends(oauth2_scheme),
    lesson_controller: LessonsController = Depends(InternalProvider().get_lessons_controller),
    # document_controller: DocumentsController = Depends(InternalProvider().get_documents_controller),
    professor_controller: ProfessorController = Depends(InternalProvider().get_professor_controller),
):
    """
    Updates an existing lesson with optional documents and descriptions.
    """
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")
    
    user = await professor_controller.professor_repository.first(where_=[Professor.id == user_id])
    if not user:
        raise NotFoundException(message="Only professors have the permission to update this lesson.")
    
    lesson = await lesson_controller.lessons_repository.first(
        where_=[Lessons.id == lesson_id],
        relations=[Lessons.course],
    )
    if not lesson:
        raise NotFoundException(message="Lesson not found for the given ID.")

    if not lesson.course:
        raise NotFoundException(message="Lesson not associated with any course.")

    if user.id != lesson.course.professor_id:
        raise BadRequestException(message="You are not allowed to update lesson in this course.")
    
    # Update the lesson
    updated_lesson = await lesson_controller.lessons_repository.update(
        where_=[Lessons.id == lesson_id],
        attributes={
            "learning_outcomes": learning_outcomes,
            "title": title,
            "description": description,
            "order": order,
        },
        commit=True,
    )

    # documents = []
    # if files:
    #     if description_file and len(files) != len(description_file):
    #         raise BadRequestException(message="Number of descriptions must match number of files.")

    #     for file, desc in zip(files, description_file or []):
    #         if file.filename:
    #             content = await file.read()

    #             s3_key = await upload_to_s3(
    #                 file_content=content,
    #                 file_name=file.filename,
    #             )
                
    #             document_data = {
    #                 "name": file.filename,
    #                 "type": file.content_type,
    #                 "document_url": s3_key,
    #                 "description": desc,
    #                 "lesson_id": lesson_id,
    #             }
    #             created_document = await document_controller.documents_repository.create(
    #                 document_data,
    #                 commit=True,
    #             )
    #             documents.append(created_document)

    # Fetch the updated documents to include in response
    # all_documents = await document_controller.documents_repository.all(
    #     where_=[Documents.lesson_id == lesson_id]
    # )

    return Ok(
        data=PutLessonResponse(
            lesson_id=updated_lesson.id,
            title=updated_lesson.title,
            description=updated_lesson.description,
            order=updated_lesson.order,
            learning_outcomes=updated_lesson.learning_outcomes,
            # documents=[DocumentResponse(**doc.__dict__) for doc in documents if doc],
        ),
        message="Successfully updated the lesson.",
    )


@router.delete("/{lesson_id}", response_model=Ok[DeleteLessonResponse])
async def delete_lesson(
    lesson_id: UUID,
    token: str = Depends(oauth2_scheme),
    lesson_controller: LessonsController = Depends(InternalProvider().get_lessons_controller),
    recommend_lesson_controller: RecommendLessonsController = Depends(
        InternalProvider().get_recommendlessons_controller
    ),
    document_controller: DocumentsController = Depends(InternalProvider().get_documents_controller),
    professor_controller: ProfessorController = Depends(InternalProvider().get_professor_controller),
):
    """
    Deletes a lesson by its ID, ensuring all related entities are also deleted.
    """
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")
    user = await professor_controller.professor_repository.first(where_=[Professor.id == user_id])
    if not user:
        raise NotFoundException(message="Only professors have the permission to delete this lesson.")
    lesson = await lesson_controller.lessons_repository.first(
        where_=[Lessons.id == lesson_id],
        relations=[
            Lessons.documents,
            Lessons.recommend_lesson,
            Lessons.course,
        ],
    )
    if not lesson:
        raise NotFoundException(message="Lesson not found for the given ID.")
    if not lesson.course:
        raise NotFoundException(message="Lesson not associated with any course.")
    if not lesson.course.professor_id == user.id:
        raise BadRequestException(message="You are not allowed to delete lesson in this course.")
    
    try:
        # Delete related RecommendLessons
        if lesson.recommend_lesson:
            await recommend_lesson_controller.recommend_lessons_repository.delete(
                where_=[RecommendLessons.lesson_id == lesson_id],
                synchronize_session=SynchronizeSessionEnum.FETCH,
            )
        # Delete related Documents
        if lesson.documents:
            await document_controller.documents_repository.delete(
                where_=[Documents.lesson_id == lesson_id],
                synchronize_session=SynchronizeSessionEnum.FETCH,
            )
        # Delete the lesson itself
        deleted_lesson = await lesson_controller.lessons_repository.delete(
            where_=[Lessons.id == lesson_id],
            synchronize_session=SynchronizeSessionEnum.FETCH,
        )
        
        # Explicitly commit the transaction
        await lesson_controller.lessons_repository.session.commit()
        
        if not deleted_lesson:
            raise Exception("Failed to delete the lesson.")
            
        return Ok(
            data=DeleteLessonResponse(
                lesson_id=lesson.id,
                title=lesson.title,
                description=lesson.description,
                order=lesson.order,
                learning_outcomes=lesson.learning_outcomes,
            ),
            message="Successfully deleted the lesson.",
        )
    except Exception as e:
        await lesson_controller.lessons_repository.session.rollback()
        raise Exception(f"Error deleting lesson: {str(e)}")

@router.post("/documents", response_model=Ok[List[DocumentResponse]])
async def add_documents(
    lesson_id: UUID = Form(...),
    files: List[UploadFile] = File(...),
    descriptions: List[str] = Form(...),
    token: str = Depends(oauth2_scheme),
    document_controller: DocumentsController = Depends(InternalProvider().get_documents_controller),
    professor_controller: ProfessorController = Depends(InternalProvider().get_professor_controller),
    lesson_controller: LessonsController = Depends(InternalProvider().get_lessons_controller),
):
    """
    Adds multiple documents to a specific lesson.
    """
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")

    user = await professor_controller.professor_repository.first(where_=[Professor.id == user_id])
    if not user:
        raise NotFoundException(message="Only professors have the permission to upload document.")

    lesson = await lesson_controller.lessons_repository.first(
        where_=[Lessons.id == lesson_id],
        relations=[
            Lessons.course,
        ],
    )
    if not lesson:
        raise NotFoundException(message="Lesson not found for the given ID.")
    if not lesson.course:
        raise NotFoundException(message="Lesson not associated with any course.")
    if not lesson.course.professor_id == user.id:
        raise BadRequestException(message="You are not allowed to add documents to this lesson.")
    
    
    # Validate that files are provided
    if not files or all(file.filename == "" for file in files):
        raise ValueError("No files provided for upload.")
    if len(files) != len(descriptions):
        raise BadRequestException(message="Number of descriptions must match number of files")
    documents = []

    for file,description in zip(files, descriptions):
        if file.filename:
            content = await file.read()

            s3_key = await upload_to_s3(
                file_content=content,
                file_name=file.filename,
            )

            document_data = {
                "name": file.filename,
                "type": file.content_type,
                "document_url": s3_key,
                "description": description,
                "lesson_id": lesson_id,
            }

            created_document = await document_controller.documents_repository.create(document_data, commit=True)

            documents.append(created_document)

    return Ok(
        data=[DocumentResponse(**doc.__dict__) for doc in documents],
        message="Successfully added the documents.",
    )

@router.get("/{lessonId}", response_model=Ok[PutLessonResponse])
async def get_lesson(
    lessonId: UUID,
    token: str = Depends(oauth2_scheme),
    lesson_controller: LessonsController = Depends(InternalProvider().get_lessons_controller),
):
    """
    Retrieves a specific lesson by its ID along with associated documents.
    """
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")
    
    lesson = await lesson_controller.lessons_repository.first(
        where_=[Lessons.id == lessonId],
        relations=[Lessons.course],
    )
    
    if not lesson:
        raise NotFoundException(message="Lesson not found for the given ID.")
    
    # # Fetch documents associated with this lesson
    # documents = await document_controller.documents_repository.get_many(
    #     where_=[Documents.lesson_id == lessonId]
    # )
    
    # documents_response = [
    #     DocumentResponse(
    #         id=doc.id,
    #         name=doc.name,
    #         type=doc.type,
    #         document_url=generate_presigned_url(doc.document_url),
    #         description=doc.description,
    #         lesson_id=lessonId
    #     )
    #     for doc in documents
    # ]
    
    return Ok(
        data=PutLessonResponse(
            lesson_id=lesson.id,
            title=lesson.title,
            description=lesson.description,
            course_id=lesson.course_id,
            order=lesson.order,
            learning_outcomes=lesson.learning_outcomes,
            # documents=documents_response,
            # lesson_id=lessonId
        ),
        message="Successfully retrieved the lesson.",
    )
@router.get("/{lessonId}/documents", response_model=Ok[List[GetDocumentResponse]])
async def get_documents(
    lessonId: UUID,
    token: str = Depends(oauth2_scheme),
    document_controller: DocumentsController = Depends(InternalProvider().get_documents_controller),
):
    """
    Retrieves all documents associated with a specific lesson.
    """
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")

    documents = await document_controller.documents_repository.get_many(where_=[Documents.lesson_id == lessonId])

    documents_response = [
        GetDocumentResponse(
            id=doc.id,
            name=doc.name,
            type=doc.type,
            document_url=generate_presigned_url(doc.document_url),
            description=doc.description,
        )
        for doc in documents
    ]

    return Ok(data=documents_response, message="Successfully retrieved the documents.")
