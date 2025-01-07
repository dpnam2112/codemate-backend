import os
import jwt
import random
import string
import httpx
from fastapi import Depends
from core.response import Ok
from fastapi import APIRouter
from core.exceptions import *
from dotenv import load_dotenv
from fastapi_mail import FastMail
from machine.models import Student
from machine.controllers.user import *
from datetime import datetime, timedelta
from passlib.context import CryptContext
from utils.excel_utils import ExcelUtils
from utils.functions import validate_email
from fastapi import HTTPException
from machine.schemas.requests.auth import *
from machine.providers import InternalProvider
from datetime import datetime, timedelta, timezone
from core.utils.email import conf, send_email_to_user


load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY") 
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30)) 
EXCEL_FILE_PATH = os.getenv("EXCEL_FILE_PATH", "backend/data/emails.xlsx")
CLIENT_AUTH = os.getenv("CLIENT_AUTH")

fm = FastMail(conf)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter(prefix="/auth", tags=["auth"])



def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = {"sub": str(data["sub"])}
    
    current_time = datetime.now(timezone(timedelta(hours=7)))
    
    if expires_delta:
        expire = current_time + expires_delta
    else:
        expire = current_time + timedelta(minutes=15)
    
    exp_timestamp = int(expire.timestamp())
    print(f"Token will expire at: {datetime.fromtimestamp(exp_timestamp)} (timestamp: {exp_timestamp})")
    
    to_encode.update({"exp": exp_timestamp})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def generate_code(length: int = 6) -> str:
    return "".join(random.choices(string.digits, k=length))

def get_role_from_excel(email: str):
    excel_professors = ExcelUtils(EXCEL_FILE_PATH, 'Professor') 
    if excel_professors.check_email_exist(email):
        return "professor"

    excel_admins = ExcelUtils(EXCEL_FILE_PATH, 'Admin') 
    if excel_admins.check_email_exist(email):
        return "admin"

    return None

async def verify_google_token(access_token: str):
    google_api_url = os.getenv("GOOGLE_API_URL")  # Get the URL from the environment variable
    
    if not google_api_url:
        raise ValueError("Google API URL is not set in the environment variables.")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f'{google_api_url}{access_token}')
    
    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Invalid Google token")
    
    return response.json()

@router.post("/login")
async def login(
    request: LoginRequest,
    student_controller: StudentController = Depends(InternalProvider().get_student_controller),
    professor_controller: ProfessorController = Depends(InternalProvider().get_professor_controller),
    admin_controller: AdminController = Depends(InternalProvider().get_admin_controller)
):
    """
    Login User
    """
    if not request.email or not request.password:
        raise UnauthorizedException("Email and password are required.")
    if not validate_email(request.email):
        raise UnauthorizedException("Invalid email")
    
    role = get_role_from_excel(request.email)
    
    user = None
    role_response = None 

    if role == "professor":
        user = await professor_controller.professor_repository.first(where_=[Professor.email == request.email])
        role_response = "professor"
    elif role == "admin":
        user = await admin_controller.admin_repository.first(where_=[Admin.email == request.email])
        role_response = "admin"
    else:
        user = await student_controller.student_repository.first(where_=[Student.email == request.email])
        role_response = "student"

    if not user:
        code = generate_code()
        await send_email_to_user(request.email, code)

        user_attributes = {
            "name": request.email.split("@")[0],
            "email": request.email,
            "password": hash_password(request.password),
            "verification_code": code,
            "verification_code_expires_at": datetime.utcnow() + timedelta(minutes=10),
            "is_email_verified": False, 
        }

        if role == "professor":
            new_user = await professor_controller.professor_repository.create(attributes=user_attributes, commit=True)
        elif role == "admin":
            new_user = await admin_controller.admin_repository.create(attributes=user_attributes, commit=True)
        else:
            new_user = await student_controller.student_repository.create(attributes=user_attributes, commit=True)
        
        user_response = {
            "id": new_user.id,
            "name": new_user.name,
            "email": new_user.email,
            "is_email_verified": new_user.is_email_verified,
            "verification_code": new_user.verification_code,
            "verification_code_expires_at": new_user.verification_code_expires_at,
        }
        
        return Ok(
            data=user_response, 
            message="User not found. Verification code sent to email"
        )
    
    if not pwd_context.verify(request.password, user.password):
        raise UnauthorizedException("Invalid password")
    
    if not user.is_email_verified:
        raise UnauthorizedException("Email is not verified. Please verify your email.")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    print(f"Creating token with {ACCESS_TOKEN_EXPIRE_MINUTES} minutes expiration")
    access_token = create_access_token(
        data={"sub": user.id}, 
        expires_delta=access_token_expires
    )

    user_response = {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "is_email_verified": user.is_email_verified,
    }

    return Ok(
        data={"access_token": access_token, "token_type": "bearer", "role": role_response, **user_response},
        message="Login successfully"
    )

@router.post("/verify-email")
async def verify_email(
    request: VerifyEmailRequest,
    student_controller: StudentController = Depends(InternalProvider().get_student_controller),
    professor_controller: ProfessorController = Depends(InternalProvider().get_professor_controller),
    admin_controller: AdminController = Depends(InternalProvider().get_admin_controller)
):
    """
    Verify Email Address for Student, Professor, and Admin
    """
    if not request.email or not request.code:
        raise UnauthorizedException("Email and code are required")
    
    role = get_role_from_excel(request.email)
    user = None

    if role == "professor":
        user = await professor_controller.professor_repository.first(where_=[Professor.email == request.email])
    elif role == "admin":
        user = await admin_controller.admin_repository.first(where_=[Admin.email == request.email])
    else:
        user = await student_controller.student_repository.first(where_=[Student.email == request.email])

    if not user:
        raise NotFoundException("User not found")

    if request.code != user.verification_code:
        raise UnauthorizedException("Invalid verification code")

    if user.verification_code_expires_at < datetime.utcnow():
        raise UnauthorizedException("Verification code has expired")

    update_attributes = {
        "is_email_verified": True,
        "is_active": True,
    }

    if role == "professor":
        updated_user = await professor_controller.professor_repository.update(where_=[Professor.email == request.email], attributes=update_attributes, commit=True)
    elif role == "admin":
        updated_user = await admin_controller.admin_repository.update(where_=[Admin.email == request.email], attributes=update_attributes, commit=True)
    else:
        updated_user = await student_controller.student_repository.update(where_=[Student.email == request.email], attributes=update_attributes, commit=True)
    
    response = {
        "id": updated_user.id,
        "name": updated_user.name,
        "email": updated_user.email,
        "is_email_verified": updated_user.is_email_verified,
        "verification_code": updated_user.verification_code,
        "verification_code_expires_at": updated_user.verification_code_expires_at,
    }

    return Ok(data=response, message="Email verified successfully")


@router.post("/resend-verification-code")
async def resend_verification_code(
    request: ResendVerificationCodeRequest,
    student_controller: StudentController = Depends(InternalProvider().get_student_controller),
    professor_controller: ProfessorController = Depends(InternalProvider().get_professor_controller),
    admin_controller: AdminController = Depends(InternalProvider().get_admin_controller)
):
    """
    Resend Verification Code for Student, Professor, and Admin
    """
    if not request.email:
        raise UnauthorizedException("Email is required")
    
    role = get_role_from_excel(request.email)
    user = None

    if role == "professor":
        user = await professor_controller.professor_repository.first(where_=[Professor.email == request.email])
    elif role == "admin":
        user = await admin_controller.admin_repository.first(where_=[Admin.email == request.email])
    else:
        user = await student_controller.student_repository.first(where_=[Student.email == request.email])
    
    if not user:
        raise NotFoundException("User not found")

    code = generate_code()
    
    await send_email_to_user(request.email, code)

    update_attributes = {
        "verification_code": code,
        "verification_code_expires_at": datetime.utcnow() + timedelta(minutes=10)
    }

    if role == "professor":
        updated_user = await professor_controller.professor_repository.update(where_=[Professor.email == request.email], attributes=update_attributes, commit=True)
    elif role == "admin":
        updated_user = await admin_controller.admin_repository.update(where_=[Admin.email == request.email], attributes=update_attributes, commit=True)
    else:
        updated_user = await student_controller.student_repository.update(where_=[Student.email == request.email], attributes=update_attributes, commit=True)
    
    response = {
        "id": updated_user.id,
        "name": updated_user.name,
        "email": updated_user.email,
        "is_email_verified": updated_user.is_email_verified,
        "verification_code": updated_user.verification_code,
        "verification_code_expires_at": updated_user.verification_code_expires_at,
    }

    return Ok(data=response, message="Resend verification code successfully")


@router.post("/forgot-password")
async def forgot_password(
    request: ForgotPasswordRequest,
    student_controller: StudentController = Depends(InternalProvider().get_student_controller),
    professor_controller: ProfessorController = Depends(InternalProvider().get_professor_controller),
    admin_controller: AdminController = Depends(InternalProvider().get_admin_controller)
):
    """Forgot Password Handle for Student, Professor, and Admin
    """
    if not request.email:
        raise UnauthorizedException("Email is required!")
    
    role = get_role_from_excel(request.email)
    user = None

    if role == "professor":
        user = await professor_controller.professor_repository.first(where_=[Professor.email == request.email])
    elif role == "admin":
        user = await admin_controller.admin_repository.first(where_=[Admin.email == request.email])
    else:
        user = await student_controller.student_repository.first(where_=[Student.email == request.email])
    
    if not user:
        raise UnauthorizedException("User not found")
    
    code = generate_code()
    
    await send_email_to_user(request.email, code, template_name="forgot-template.html")

    update_attributes = {
        "password_reset_code": code,
        "password_reset_code_expires_at": datetime.utcnow() + timedelta(minutes=10)
    }

    if role == "professor":
        updated_user = await professor_controller.professor_repository.update(where_=[Professor.email == request.email], attributes=update_attributes, commit=True)
    elif role == "admin":
        updated_user = await admin_controller.admin_repository.update(where_=[Admin.email == request.email], attributes=update_attributes, commit=True)
    else:
        updated_user = await student_controller.student_repository.update(where_=[Student.email == request.email], attributes=update_attributes, commit=True)
    
    response = {
        "id": updated_user.id,
        "name": updated_user.name,
        "email": updated_user.email,
        "is_email_verified": updated_user.is_email_verified,
        "password_reset_code": updated_user.password_reset_code,
        "password_reset_code_expires_at": updated_user.password_reset_code_expires_at,
    }

    return Ok(data=response, message="Sent code to reset password successfully")

@router.post("/reset-password")
async def reset_password(
    request: ResetPasswordRequest,
    student_controller: StudentController = Depends(InternalProvider().get_student_controller),
    professor_controller: ProfessorController = Depends(InternalProvider().get_professor_controller),
    admin_controller: AdminController = Depends(InternalProvider().get_admin_controller)
):
    """Reset Password Handle for Student, Professor, and Admin
    """
    if not request.email or not request.code or not request.new_password:
        raise UnauthorizedException("Email, code, and password are required")
    
    role = get_role_from_excel(request.email)
    user = None

    if role == "professor":
        user = await professor_controller.professor_repository.first(where_=[Professor.email == request.email])
    elif role == "admin":
        user = await admin_controller.admin_repository.first(where_=[Admin.email == request.email])
    else:
        user = await student_controller.student_repository.first(where_=[Student.email == request.email])
    
    if not user:
        raise UnauthorizedException("User not found")
    
    if request.code != user.password_reset_code:
        raise UnauthorizedException("Invalid reset code")
    
    if user.password_reset_code_expires_at < datetime.utcnow():
        raise UnauthorizedException("Reset code has expired")
    
    update_attributes = {
        "password": hash_password(request.new_password),
        "password_reset_code": None,
        "password_reset_code_expires_at": None
    }

    if role == "professor":
        updated_user = await professor_controller.professor_repository.update(where_=[Professor.email == request.email], attributes=update_attributes, commit=True)
    elif role == "admin":
        updated_user = await admin_controller.admin_repository.update(where_=[Admin.email == request.email], attributes=update_attributes, commit=True)
    else:
        updated_user = await student_controller.student_repository.update(where_=[Student.email == request.email], attributes=update_attributes, commit=True)
    
    response = {
        "id": updated_user.id,
        "name": updated_user.name,
        "email": updated_user.email,
        "is_email_verified": updated_user.is_email_verified,
    }

    return Ok(data=response, message="Reset password successfully")

@router.post("/google-login")
async def google_login(
    auth_request: GoogleAuthRequest,
):
    google_token_info = await verify_google_token(auth_request.access_token)

    if google_token_info['email'] != auth_request.email:
        raise UnauthorizedException("Email does not match")

    user_info = {
        "email": google_token_info['email'],
    }

    return Ok(data=user_info, message="Google login successfully")
    
    