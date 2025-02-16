from typing import List, Union
from sqlalchemy import or_, and_, select
from fastapi import APIRouter, Depends, Query
from core.response import Ok
from core.exceptions import *
from machine.controllers import *
from machine.models import *
from machine.providers import InternalProvider
from core.utils.auth_utils import verify_token
from fastapi.security import OAuth2PasswordBearer
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
router = APIRouter(prefix="/users", tags=["users"])

@router.get("/count")
async def count_user(
    role: str = Query(None),  
    token: str = Depends(oauth2_scheme),
    student_controller: StudentController = Depends(InternalProvider().get_student_controller),
    professor_controller: ProfessorController = Depends(InternalProvider().get_professor_controller),
    admin_controller: AdminController = Depends(InternalProvider().get_admin_controller),
):
    payload = verify_token(token)
    user_id = payload.get("sub")

    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")

    check_role = await admin_controller.admin_repository.first(where_=Admin.id == user_id)
    if not check_role:
        raise ForbiddenException(message="You are not allowed to access this feature.")

    if not role: 
        total_count = (
            await student_controller.student_repository.count()
            + await professor_controller.professor_repository.count()
            + await admin_controller.admin_repository.count()
        )
        return Ok(data=total_count, message="Counted all users")

    role_mapping = {
        "student": student_controller.student_repository.count,
        "professor": professor_controller.professor_repository.count,
        "admin": admin_controller.admin_repository.count
    }
    
    if role in role_mapping:
        count = await role_mapping[role]()
        return Ok(data=count, message=f"Counted {role}s")
    
    raise BadRequestException("Invalid role")

@router.get("/{user_id}", description="Get user information")
async def get_user_information(
    user_id: str,
    token: str = Depends(oauth2_scheme),
    student_controller: StudentController = Depends(InternalProvider().get_student_controller),
    professor_controller: ProfessorController = Depends(InternalProvider().get_professor_controller),
    admin_controller: AdminController = Depends(InternalProvider().get_admin_controller),
):
    payload = verify_token(token)
    user_id_from_token = payload.get("sub")

    if not user_id_from_token:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")

    check_role = await admin_controller.admin_repository.first(where_=Admin.id == user_id_from_token)
    if not check_role:
        raise ForbiddenException(message="You are not allowed to access this feature.")

    check_user = await student_controller.student_repository.first(where_=Student.id == user_id)
    if not check_user:
        check_user = await professor_controller.professor_repository.first(where_=Professor.id == user_id)
        if not check_user:
            check_user = await admin_controller.admin_repository.first(where_=Admin.id == user_id)
            if not check_user:
                raise NotFoundException(message="User not found")
    user_response = {
        "id": check_user.id,
        "name": check_user.name,
        "email": check_user.email,
    }
    return Ok(data=user_response, message="User information")
@router.get("/", description="Get all users")
async def get_all_users(
    role: str = Query(None, title="Role", description="Filter by role", example="student"),
    status: str = Query(None, title="Status", description="Filter by status", example="True"),
    search_query: str = Query(None, title="Search by ms or email", description="Filter by ms or email", example="211"),
    token: str = Depends(oauth2_scheme),
    student_controller: StudentController = Depends(InternalProvider().get_student_controller),
    professor_controller: ProfessorController = Depends(InternalProvider().get_professor_controller),
    admin_controller: AdminController = Depends(InternalProvider().get_admin_controller),
):
    payload = verify_token(token)
    user_id = payload.get("sub")

    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")

    check_role = await admin_controller.admin_repository.first(where_=[Admin.id == user_id])
    if not check_role:
        raise ForbiddenException(message="You are not allowed to access this feature.")

    try:
        users = []
        is_active_filter = None if status is None else (status.lower() == "true")

        if role:
            if role == "student":
                where_conditions = []
                if status is not None:
                    where_conditions.append(Student.is_active == is_active_filter)
                if search_query:
                    where_conditions.append(
                        or_(
                            Student.mssv.like(f"%{search_query}%"),
                            Student.email.like(f"%{search_query}%")
                        )
                    )
                
                students = await student_controller.student_repository.get_many(where_=where_conditions)
                users = [
                    {
                        "id": student.id,
                        "name": student.name,
                        "email": student.email,
                        "ms": student.mssv,
                        "date_of_birth": student.date_of_birth,
                        "status": student.is_active,
                        "fullname": student.fullname,
                        "role": "student"
                    }
                    for student in students
                ]

            elif role == "professor":
                where_conditions = []
                if status is not None:
                    where_conditions.append(Professor.is_active == is_active_filter)
                if search_query:
                    where_conditions.append(
                        or_(
                            Professor.mscb.like(f"%{search_query}%"),
                            Professor.email.like(f"%{search_query}%")
                        )
                    )
                
                professors = await professor_controller.professor_repository.get_many(where_=where_conditions)
                users = [
                    {
                        "id": professor.id,
                        "name": professor.name,
                        "email": professor.email,
                        "ms": professor.mscb,
                        "date_of_birth": professor.date_of_birth,
                        "status": professor.is_active,
                        "fullname": professor.fullname,
                        "role": "professor"
                    }
                    for professor in professors
                ]

            elif role == "admin":
                where_conditions = []
                if status is not None:
                    where_conditions.append(Admin.is_active == is_active_filter)
                if search_query:
                    where_conditions.append(
                        or_(
                            Admin.mscb.like(f"%{search_query}%"),
                            Admin.email.like(f"%{search_query}%")
                        )
                    )
                
                admins = await admin_controller.admin_repository.get_many(where_=where_conditions)
                users = [
                    {
                        "id": admin.id,
                        "name": admin.name,
                        "email": admin.email,
                        "ms": admin.mscb,
                        "date_of_birth": admin.date_of_birth,
                        "status": admin.is_active,
                        "fullname": admin.fullname,
                        "role": "admin"
                    }
                    for admin in admins
                ]
            else:
                raise BadRequestException(message="Invalid role. Must be one of 'student', 'professor', or 'admin'.")
        else:
            # Get all users when no role is specified
            # Students
            student_conditions = []
            if status is not None:
                student_conditions.append(Student.is_active == is_active_filter)
            if search_query:
                student_conditions.append(
                    or_(
                        Student.mssv.like(f"%{search_query}%"),
                        Student.email.like(f"%{search_query}%")
                    )
                )
            students = await student_controller.student_repository.get_many(where_=student_conditions)
            
            # Professors
            professor_conditions = []
            if status is not None:
                professor_conditions.append(Professor.is_active == is_active_filter)
            if search_query:
                professor_conditions.append(
                    or_(
                        Professor.mscb.like(f"%{search_query}%"),
                        Professor.email.like(f"%{search_query}%")
                    )
                )
            professors = await professor_controller.professor_repository.get_many(where_=professor_conditions)
            
            # Admins
            admin_conditions = []
            if status is not None:
                admin_conditions.append(Admin.is_active == is_active_filter)
            if search_query:
                admin_conditions.append(
                    or_(
                        Admin.mscb.like(f"%{search_query}%"),
                        Admin.email.like(f"%{search_query}%")
                    )
                )
            admins = await admin_controller.admin_repository.get_many(where_=admin_conditions)

            # Combine results
            users = [
                {
                    "id": student.id,
                    "name": student.name,
                    "email": student.email,
                    "ms": student.mssv,
                    "date_of_birth": student.date_of_birth,
                    "status": student.is_active,
                    "fullname": student.fullname,
                    "role": "student"
                }
                for student in students
            ]
            users.extend([
                {
                    "id": professor.id,
                    "name": professor.name,
                    "email": professor.email,
                    "ms": professor.mscb,
                    "date_of_birth": professor.date_of_birth,
                    "status": professor.is_active,
                    "fullname": professor.fullname,
                    "role": "professor"
                }
                for professor in professors
            ])
            users.extend([
                {
                    "id": admin.id,
                    "name": admin.name,
                    "email": admin.email,
                    "ms": admin.mscb,
                    "date_of_birth": admin.date_of_birth,
                    "status": admin.is_active,
                    "fullname": admin.fullname,
                    "role": "admin"
                }
                for admin in admins
            ])

        return Ok(data=users, message="Filtered users")
    except Exception as e:
        raise SystemException(f"Error fetching users: {str(e)}")