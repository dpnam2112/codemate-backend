from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from fastapi import FastAPI, File, UploadFile, Form
from datetime import datetime
from core.repository.enum import DifficultyLevel, QuestionType
# class DocumentRequest(BaseModel):
#     name: str
#     type: str
#     document_url: str
# class CreateNewLessonRequest(BaseModel):
#     title: str
#     description: Optional[str]
#     order: int
#     learning_outcomes: Optional[list[str]]
#     documents: Optional[list[DocumentRequest]]
#     course_id: UUID
class DocumentRequest(BaseModel):
    name: str = Form(...)
    type: str= Form(...)
    document_url: str= Form(...)
    file: Optional[UploadFile] = File(...)
class CreateNewLessonRequest(BaseModel):
    title: str = Form(...)
    description: Optional[str] = Form(...)
    order: int = Form(...)
    learning_outcomes: Optional[list[str]] = Form(...)
    documents: Optional[list[DocumentRequest]] = Form(...)
    course_id: UUID = Form(...)

class PutLessonRequest(BaseModel):
    lesson_id: UUID
    title: str
    description: Optional[str]
    order: int
    learning_outcomes: Optional[list[str]]
    
class DeleteLessonRequest(BaseModel):
    lesson_id: UUID
    
