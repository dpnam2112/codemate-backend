import logging
from typing import List, Union
from sqlalchemy import or_, and_, select
from fastapi import APIRouter, Depends, Query, File, Form, UploadFile
from core.response import Ok
from core.exceptions import *
from machine.controllers import *
from machine.models import *
from machine.providers import InternalProvider
from machine.schemas.requests.user import *
from core.utils.auth_utils import verify_token
from fastapi.security import OAuth2PasswordBearer
from core.utils.file import *
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
router = APIRouter(prefix="/users", tags=["users"])

@router.post("/", description="Create a new user")
async def create_user(
    user: Union[UserCreate, List[UserCreate]], 
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

    if isinstance(user, list):
        new_users = []
        for user_data in user:
            new_user = await _create_individual_user(user_data, student_controller, professor_controller, admin_controller)
            new_users.append(new_user)
        return Ok(data=new_users, message="Users created successfully")

    new_user = await _create_individual_user(user, student_controller, professor_controller, admin_controller)
    return Ok(data=new_user, message="User created successfully")

async def _create_individual_user(
    user: UserCreate,
    student_controller: StudentController,
    professor_controller: ProfessorController,
    admin_controller: AdminController,
):
    if user.role == UserRole.student:
        user_attributes = {
            "name": user.name if user.name else user.fullname,
            "fullname": user.fullname,
            "email": user.email,
            "date_of_birth": user.date_of_birth,
            "mssv": user.ms,
        }
        created_user = await student_controller.student_repository.create(attributes=user_attributes, commit=True)
        return created_user.to_dict() if hasattr(created_user, 'to_dict') else created_user.__dict__

    elif user.role == UserRole.professor:
        user_attributes = {
            "name": user.name if user.name else user.fullname,
            "fullname": user.fullname,
            "email": user.email,
            "date_of_birth": user.date_of_birth,
            "mscb": user.ms,
        }
        created_user = await professor_controller.professor_repository.create(attributes=user_attributes, commit=True)
        return created_user.to_dict() if hasattr(created_user, 'to_dict') else created_user.__dict__

    elif user.role == UserRole.admin:
        user_attributes = {
            "name": user.name if user.name else user.fullname,
            "fullname": user.fullname,
            "email": user.email,
            "date_of_birth": user.date_of_birth,
            "mscb": user.ms,
        }
        created_user = await admin_controller.admin_repository.create(attributes=user_attributes, commit=True)
        return created_user.to_dict() if hasattr(created_user, 'to_dict') else created_user.__dict__

    else:
        raise BadRequestException(message="Invalid role provided for user")
    
@router.patch("/", description="Update user information") 
async def update_user_information(
    name: str = Form(None),
    fullname: str = Form(None),
    date_of_birth: date = Form(None),
    role: UserRole = Form(...),
    file: UploadFile = File(None),
    token: str = Depends(oauth2_scheme),
    student_controller: StudentController = Depends(InternalProvider().get_student_controller),
    professor_controller: ProfessorController = Depends(InternalProvider().get_professor_controller),
    admin_controller: AdminController = Depends(InternalProvider().get_admin_controller),
):
    
    '''
    Update user information
    
    Args:
    user: UserUpdate: User information to be updated (fullname, name, date_of_birth, role)
    token: str: JWT token for authorization. Based on user role, the user can update their own information or other users' information.
    
    '''
    payload = verify_token(token)
    user_id_from_token = payload.get("sub")

    if not user_id_from_token:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")

    # Determine the role of the user by checking their presence in the tables
    check_user = None
    user_role = None
    

    # Check for student first
    check_user = await student_controller.student_repository.first(where_=[Student.id == user_id_from_token])
    if check_user:
        user_role = "student"
    
    # If not a student, check for professor
    if not check_user:
        check_user = await professor_controller.professor_repository.first(where_=[Professor.id == user_id_from_token])
        if check_user:
            user_role = "professor"

    # If not a professor, check for admin
    if not check_user:
        check_user = await admin_controller.admin_repository.first(where_=[Admin.id == user_id_from_token])
        if check_user:
            user_role = "admin"

    # If the user is not found in any of the tables, raise a NotFoundException
    if not check_user:
        raise NotFoundException(message="User not found")

    # Now that we know the role, check if the role matches the request
    if user_role == "student":
        if role != UserRole.student:
            raise BadRequestException(message=f"You cannot change the role of a student {user_role} {role}")
        user_attributes = {}
        
        if fullname:
            user_attributes["fullname"] = fullname
        if name:
            user_attributes["name"] = name
        if date_of_birth:
            user_attributes["date_of_birth"] = date_of_birth
        if file:
            file_content = await file.read()
            s3_key = await upload_to_s3(file_content, file.filename)
            user_attributes["avatar_url"] = s3_key
        
        try:
            await student_controller.student_repository.update(
                where_=[Student.id == user_id_from_token], attributes=user_attributes, commit=True
            )
        except Exception as e:
            raise SystemException(f"Error updating student information: {str(e)}")
            
        return Ok(data=True, message="Student information updated successfully")

    elif user_role == "professor":
        if role != UserRole.professor:
            raise BadRequestException(message=f"You cannot change the role of a professor {user_role} {role}")

        user_attributes = {}
        
        if fullname:
            user_attributes["fullname"] = fullname
        if name:
            user_attributes["name"] = name
        if date_of_birth:
            user_attributes["date_of_birth"] = date_of_birth
        if file:
            file_content = await file.read()
            s3_key = await upload_to_s3(file_content, file.filename)
            user_attributes["avatar_url"] = s3_key
        
        try: 
            await professor_controller.professor_repository.update(
            where_=[Professor.id == user_id_from_token], attributes=user_attributes, commit=True
        )
        except Exception as e:
            raise SystemException(f"Error updating professor information: {str(e)}")
            
        return Ok(data=True, message="Professor information updated successfully")

    elif user_role == "admin":
        if role != UserRole.admin:
            raise BadRequestException(message=f"You cannot change the role of an admin {user_role} {role}")

        user_attributes = {}
        
        if fullname:
            user_attributes["fullname"] = fullname
        if name:
            user_attributes["name"] = name
        if date_of_birth:
            user_attributes["date_of_birth"] = date_of_birth
        if file:
            file_content = await file.read()
            s3_key = await upload_to_s3(file_content, file.filename)
            user_attributes["avatar_url"] = s3_key
        
        try: 
            await admin_controller.admin_repository.update(
            where_=[Admin.id == user_id_from_token], attributes=user_attributes, commit=True
        )
        
        except Exception as e:
            raise SystemException(f"Error updating admin information: {str(e)}")
        
        return Ok(data=True, message="Admin information updated successfully")

    else:
        raise BadRequestException(message="Invalid role provided for user")
    
@router.get("/", description="Get profile")
async def get_profile(
    token: str = Depends(oauth2_scheme),
    student_controller: StudentController = Depends(InternalProvider().get_student_controller),
    professor_controller: ProfessorController = Depends(InternalProvider().get_professor_controller),
    admin_controller: AdminController = Depends(InternalProvider().get_admin_controller),
):
    payload = verify_token(token)
    user_id = payload.get("sub")

    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")
    role = "student"
    check_user = await student_controller.student_repository.first(where_=[Student.id == user_id])
    if not check_user:
        check_user = await professor_controller.professor_repository.first(where_=[Professor.id == user_id])
        role = "professor"
        if not check_user:
            check_user = await admin_controller.admin_repository.first(where_=[Admin.id == user_id])
            role = "admin"
            if not check_user:
                raise NotFoundException(message="User not found")
    avatar_url = ""
    if check_user.avatar_url:
        if check_user.avatar_url.startswith("documents/"):
            avatar_url = generate_presigned_url(check_user.avatar_url)
        else:
            avatar_url = check_user.avatar_url
    user_response = {
        "id": check_user.id,
        "name": check_user.name,
        "fullname": check_user.fullname,
        "avatar": avatar_url,
        "email": check_user.email,
        "ms": check_user.mscb if role == "admin" or role == "professor" else check_user.mssv,
        "date_of_birth": check_user.date_of_birth,
        "role": role
    }
    return Ok(data=user_response, message="User profile")

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

@router.get("/admin", description="Get all users")
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
    
    

@router.get("/user-logs", description="Get user login logs")
async def get_user_login_logs(
    token: str = Depends(oauth2_scheme),
    admin_controller: AdminController = Depends(InternalProvider().get_admin_controller
    ),
    user_logins_controller: UserLoginsController = Depends(InternalProvider().get_user_logins_controller),
):
    payload = verify_token(token)
    user_id = payload.get("sub")

    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")

    check_role = await admin_controller.admin_repository.first(where_=Admin.id == user_id)
    if not check_role:
        raise ForbiddenException(message="You are not allowed to access this feature.")

    user_logins = await user_logins_controller.user_logins_repository.get_many()
    user_logins_response = [
        {
            "id": user_login.id,
            "user_id": user_login.user_id,
            "user_role": user_login.user_role,
            "login_timestamp": user_login.login_timestamp,
        }
        for user_login in user_logins
    ]
    return Ok(data=user_logins_response, message="User login logs")

@router.post("/user-logs", description="Create user login log")
async def create_user_login_log(
    user_login: UserLoginCreate,
    token: str = Depends(oauth2_scheme),
    admin_controller: AdminController = Depends(InternalProvider().get_admin_controller),
    user_logins_controller: UserLoginsController = Depends(InternalProvider().get_user_logins_controller),
):
    payload = verify_token(token)
    user_id = payload.get("sub")

    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")

    check_role = await admin_controller.admin_repository.first(where_=Admin.id == user_id)
    if not check_role:
        raise ForbiddenException(message="You are not allowed to access this feature.")
    
    user_logins_attributes = {
        "user_id": user_id,
        "user_role": user_login.user_role,
        "login_timestamp": user_login.login_timestamp.astimezone().replace(tzinfo=None),
    }

    created_user_login = await user_logins_controller.user_logins_repository.create(attributes=user_logins_attributes, commit=True)
    
    user_logins_response = {
        "id": created_user_login.id,
        "user_id": created_user_login.user_id,
        "user_role": created_user_login.user_role,
        "login_timestamp": created_user_login.login_timestamp
    }
    return Ok(data=user_logins_response, message="User login log created successfully")

@router.get("/{user_id}", description="Get user information for admin")
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
        "avatar": check_user.avatar_url,
        "fullname": check_user.fullname,
        "ms": check_user.mssv if hasattr(check_user, "mssv") else check_user.mscb,
    }
    return Ok(data=user_response, message="User information")

# Update status of user for admin 
@router.patch("/status/{user_id}", description="Update user status for admin")
async def update_user_status(
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
    
    if isinstance(check_user, Student):
        await student_controller.student_repository.update(
            where_=[Student.id == user_id], attributes={"is_active": not check_user.is_active}, commit=True
        )
    elif isinstance(check_user, Professor):
        await professor_controller.professor_repository.update(
            where_=[Professor.id == user_id], attributes={"is_active": not check_user.is_active}, commit=True
        )
    elif isinstance(check_user, Admin):
        await admin_controller.admin_repository.update(
            where_=[Admin.id == user_id], attributes={"is_active": not check_user.is_active}, commit=True
        )
    
    return Ok(data=True, message="User status updated successfully")