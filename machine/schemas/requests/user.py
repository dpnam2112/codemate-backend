from typing import Optional
from pydantic import BaseModel
from datetime import date
from core.repository.enum import UserRole

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
    fullname: Optional[str] = None 
    name: Optional[str] = None    
    date_of_birth: Optional[date] = None 
    role: UserRole 