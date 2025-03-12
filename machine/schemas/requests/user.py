from typing import Optional
from pydantic import BaseModel
from datetime import date, datetime
from core.repository.enum import UserRole
from fastapi import Form, File, UploadFile

class UserRequest(BaseModel):
    id: Optional[int]
    name: str

class UserCreate(BaseModel):
    name: str
    fullname: str
    email: str
    date_of_birth: date
    ms: str
    role: UserRole
    
class UserUpdate(BaseModel):
    file: Optional[UploadFile] = File(...)
    fullname: Optional[str] = Form(...) 
    name: Optional[str] = Form(...)   
    date_of_birth: Optional[date] = Form(...)
    role: UserRole = Form(...)
    
class UserLoginCreate(BaseModel):
    user_role: UserRole
    login_timestamp: datetime