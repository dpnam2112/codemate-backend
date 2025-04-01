import os
import jwt
import httpx
import random
import string
from fastapi import Depends
from core.response import Ok
from fastapi import APIRouter
from core.exceptions import *
from dotenv import load_dotenv
from fastapi_mail import FastMail
from fastapi import HTTPException
from machine.models import Student
from machine.controllers.user import *
from datetime import datetime, timedelta
from passlib.context import CryptContext
from utils.excel_utils import ExcelUtils
from utils.functions import validate_email
from machine.schemas.requests.auth import *
from machine.providers import InternalProvider
from datetime import datetime, timedelta, timezone
from core.utils.email import conf, send_email_to_user


load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
REFRESH_SECRET_KEY = os.getenv("REFRESH_SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS"))
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
    to_encode.update({"exp": exp_timestamp})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    to_encode = {"sub": str(data["sub"])}
    expire = datetime.now(timezone(timedelta(hours=7))) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": int(expire.timestamp())})
    encoded_jwt = jwt.encode(to_encode, REFRESH_SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_refresh_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, REFRESH_SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise UnauthorizedException("Refresh token has expired")
    except jwt.JWTError:
        raise UnauthorizedException("Invalid refresh token")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def generate_code(length: int = 6) -> str:
    return "".join(random.choices(string.digits, k=length))


async def check_exist_and_get_role_for_user(email: str, student_controller: StudentController, professor_controller: ProfessorController, admin_controller: AdminController):
    student = await student_controller.student_repository.first(where_=[Student.email == email])
    if student:
        return "student"

    professor = await professor_controller.professor_repository.first(where_=[Professor.email == email])
    if professor:
        return "professor"

    admin = await admin_controller.admin_repository.first(where_=[Admin.email == email])
    if admin:
        return "admin"

    return None
    


async def verify_google_token(access_token: str):
    google_api_url = os.getenv("GOOGLE_API_URL")
    if not google_api_url:
        raise ValueError("Google API URL is not set in the environment variables.")

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{google_api_url}{access_token}")

    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Invalid Google token")

    return response.json()


def create_tokens_response(user_id: str, user_data: dict) -> dict:
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user_id}, expires_delta=access_token_expires)
    refresh_token = create_refresh_token(data={"sub": user_id})

    return {"access_token": access_token, "refresh_token": refresh_token, **user_data}


@router.post("/login")
async def login(
    request: LoginRequest,
    student_controller: StudentController = Depends(InternalProvider().get_student_controller),
    professor_controller: ProfessorController = Depends(InternalProvider().get_professor_controller),
    admin_controller: AdminController = Depends(InternalProvider().get_admin_controller),
):
    """
    Login User
    """
    if not request.email or not request.password:
        raise UnauthorizedException("Email and password are required.")
    if not validate_email(request.email):
        raise UnauthorizedException("Invalid email")

    role = await check_exist_and_get_role_for_user(request.email, student_controller=student_controller, professor_controller=professor_controller, admin_controller=admin_controller)

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
            "is_email_verified": False,
            "verification_code": code,
            "verification_code_expires_at": datetime.utcnow() + timedelta(minutes=10),
        }

        if role == "professor":
            new_user = await professor_controller.professor_repository.create(attributes=user_attributes, commit=True)
        elif role == "admin":
            new_user = await admin_controller.admin_repository.create(attributes=user_attributes, commit=True)
        else:
            new_user = await student_controller.student_repository.create(attributes=user_attributes, commit=True)

        user_response = {
            "name": new_user.name,
            "email": new_user.email,
            "is_email_verified": new_user.is_email_verified,
        }

        return Ok(data=user_response, message="User not found. Verification code sent to email")

    if not user.password:
        if role == "professor":
            new_user = await professor_controller.professor_repository.update(
                where_=[Professor.email == request.email],
                attributes={"password": hash_password(request.password)},
                commit=True,
            )
        elif role == "admin":
            new_user = await admin_controller.admin_repository.update(
                where_=[Admin.email == request.email],
                attributes={"password": hash_password(request.password)},
                commit=True,
            )
        else:
            new_user = await student_controller.student_repository.update(
                where_=[Student.email == request.email],
                attributes={"password": hash_password(request.password)},
                commit=True,
            )

        user_response = {"name": new_user.name, "email": new_user.email, "is_active": True, "is_email_verified": True, "role": role_response}

        return Ok(
            data=create_tokens_response(user.id, user_response),
            message="Login successfully",
        )

    if not pwd_context.verify(request.password, user.password):
        raise UnauthorizedException("Invalid password")

    if not user.is_email_verified:
        code = generate_code()
        await send_email_to_user(request.email, code)
        user_attributes = {
            "is_email_verified": False,
            "verification_code": code,
            "verification_code_expires_at": datetime.utcnow() + timedelta(minutes=10),
        }
        if role == "professor":
            new_user = await professor_controller.professor_repository.update(
                where_=[Professor.email == request.email],
                attributes=user_attributes,
                commit=True,
            )
        elif role == "admin":
            new_user = await admin_controller.admin_repository.update(
                where_=[Admin.email == request.email],
                attributes=user_attributes,
                commit=True,
            )
        else:
            new_user = await student_controller.student_repository.update(
                where_=[Student.email == request.email],
                attributes=user_attributes,
                commit=True,
            )
        return Ok(data=None, message="Your email hasn't been verified. Please verify your email to login.")

    user_response = {
        "name": user.name,
        "email": user.email,
        "is_active": user.is_active,
        "is_email_verified": user.is_email_verified,
        "role": role_response,
    }

    return Ok(
        data=create_tokens_response(user.id, user_response),
        message="Login successfully",
    )


@router.post("/refresh-token")
async def refresh_token(
    request: RefreshTokenRequest,
    student_controller: StudentController = Depends(InternalProvider().get_student_controller),
    professor_controller: ProfessorController = Depends(InternalProvider().get_professor_controller),
    admin_controller: AdminController = Depends(InternalProvider().get_admin_controller),
):
    """
    Refresh Access Token using Refresh Token
    """
    try:
        payload = decode_refresh_token(request.refresh_token)
        user_id = payload.get("sub")

        user = None
        role_response = None

        user = await professor_controller.professor_repository.first(where_=[Professor.id == user_id])
        if user:
            role_response = "professor"
        else:
            user = await admin_controller.admin_repository.first(where_=[Admin.id == user_id])
            if user:
                role_response = "admin"
            else:
                user = await student_controller.student_repository.first(where_=[Student.id == user_id])
                if user:
                    role_response = "student"

        if not user:
            raise UnauthorizedException("User not found")

        user_response = {
            "name": user.name,
            "email": user.email,
            "is_email_verified": user.is_email_verified,
            "role": role_response,
        }

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(data={"sub": user_id}, expires_delta=access_token_expires)

        return Ok(data={"access_token": access_token, **user_response}, message="Token refreshed successfully")

    except Exception as e:
        raise UnauthorizedException(str(e))


@router.post("/verify-email")
async def verify_email(
    request: VerifyEmailRequest,
    student_controller: StudentController = Depends(InternalProvider().get_student_controller),
    professor_controller: ProfessorController = Depends(InternalProvider().get_professor_controller),
    admin_controller: AdminController = Depends(InternalProvider().get_admin_controller),
):
    """
    Verify Email Address for Student, Professor, and Admin
    """
    if not request.email or not request.code:
        raise UnauthorizedException("Email and code are required")

    role = await check_exist_and_get_role_for_user(request.email, student_controller=student_controller, professor_controller=professor_controller, admin_controller=admin_controller)
    user = None

    if role == "professor":
        user = await professor_controller.professor_repository.first(where_=[Professor.email == request.email])
    elif role == "admin":
        user = await admin_controller.admin_repository.first(where_=[Admin.email == request.email])
    else:
        user = await student_controller.student_repository.first(where_=[Student.email == request.email])

    if not user:
        raise NotFoundException("User not found")

    if request.reset_password:
        if request.code != user.password_reset_code:
            raise UnauthorizedException("Invalid reset code")
        if user.password_reset_code_expires_at < datetime.utcnow():
            raise UnauthorizedException("Reset code has expired")
    else:
        if request.code != user.verification_code:
            raise UnauthorizedException("Invalid verification code")
        if user.verification_code_expires_at < datetime.utcnow():
            raise UnauthorizedException("Verification code has expired")

    update_attributes = {
        "is_email_verified": True,
        "is_active": True,
    }

    if role == "professor":
        updated_user = await professor_controller.professor_repository.update(
            where_=[Professor.email == request.email], attributes=update_attributes, commit=True
        )
    elif role == "admin":
        updated_user = await admin_controller.admin_repository.update(
            where_=[Admin.email == request.email], attributes=update_attributes, commit=True
        )
    else:
        updated_user = await student_controller.student_repository.update(
            where_=[Student.email == request.email], attributes=update_attributes, commit=True
        )

    response = {
        "name": updated_user.name,
        "email": updated_user.email,
        "is_email_verified": updated_user.is_email_verified,
    }

    return Ok(data=response, message="Email verified successfully")


@router.post("/resend-verification-code")
async def resend_verification_code(
    request: ResendVerificationCodeRequest,
    student_controller: StudentController = Depends(InternalProvider().get_student_controller),
    professor_controller: ProfessorController = Depends(InternalProvider().get_professor_controller),
    admin_controller: AdminController = Depends(InternalProvider().get_admin_controller),
):
    """
    Resend Verification Code for Student, Professor, and Admin
    """
    if not request.email:
        raise UnauthorizedException("Email is required")

    role = await check_exist_and_get_role_for_user(request.email, student_controller=student_controller, professor_controller=professor_controller, admin_controller=admin_controller)
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
        "verification_code_expires_at": datetime.utcnow() + timedelta(minutes=10),
    }

    if role == "professor":
        updated_user = await professor_controller.professor_repository.update(
            where_=[Professor.email == request.email], attributes=update_attributes, commit=True
        )
    elif role == "admin":
        updated_user = await admin_controller.admin_repository.update(
            where_=[Admin.email == request.email], attributes=update_attributes, commit=True
        )
    else:
        updated_user = await student_controller.student_repository.update(
            where_=[Student.email == request.email], attributes=update_attributes, commit=True
        )

    response = {
        "name": updated_user.name,
        "email": updated_user.email,
        "is_email_verified": updated_user.is_email_verified,
    }

    return Ok(data=response, message="Resend verification code successfully")


@router.post("/forgot-password")
async def forgot_password(
    request: ForgotPasswordRequest,
    student_controller: StudentController = Depends(InternalProvider().get_student_controller),
    professor_controller: ProfessorController = Depends(InternalProvider().get_professor_controller),
    admin_controller: AdminController = Depends(InternalProvider().get_admin_controller),
):
    """Forgot Password Handle for Student, Professor, and Admin"""
    if not request.email:
        raise UnauthorizedException("Email is required!")

    role = await check_exist_and_get_role_for_user(request.email, student_controller=student_controller, professor_controller=professor_controller, admin_controller=admin_controller)
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
        "password_reset_code_expires_at": datetime.utcnow() + timedelta(minutes=10),
    }

    if role == "professor":
        updated_user = await professor_controller.professor_repository.update(
            where_=[Professor.email == request.email], attributes=update_attributes, commit=True
        )
    elif role == "admin":
        updated_user = await admin_controller.admin_repository.update(
            where_=[Admin.email == request.email], attributes=update_attributes, commit=True
        )
    else:
        updated_user = await student_controller.student_repository.update(
            where_=[Student.email == request.email], attributes=update_attributes, commit=True
        )

    response = {
        "name": updated_user.name,
        "email": updated_user.email,
        "is_email_verified": updated_user.is_email_verified,
    }

    return Ok(data=response, message="Sent code to reset password successfully")


@router.post("/reset-password")
async def reset_password(
    request: ResetPasswordRequest,
    student_controller: StudentController = Depends(InternalProvider().get_student_controller),
    professor_controller: ProfessorController = Depends(InternalProvider().get_professor_controller),
    admin_controller: AdminController = Depends(InternalProvider().get_admin_controller),
):
    """Reset Password Handle for Student, Professor, and Admin"""
    if not request.email or not request.code or not request.new_password:
        raise UnauthorizedException("Email, code, and password are required")

    role = await check_exist_and_get_role_for_user(request.email, student_controller=student_controller, professor_controller=professor_controller, admin_controller=admin_controller)
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
        "password_reset_code_expires_at": None,
    }

    if role == "professor":
        updated_user = await professor_controller.professor_repository.update(
            where_=[Professor.email == request.email], attributes=update_attributes, commit=True
        )
    elif role == "admin":
        updated_user = await admin_controller.admin_repository.update(
            where_=[Admin.email == request.email], attributes=update_attributes, commit=True
        )
    else:
        updated_user = await student_controller.student_repository.update(
            where_=[Student.email == request.email], attributes=update_attributes, commit=True
        )

    response = {
        "name": updated_user.name,
        "email": updated_user.email,
        "is_email_verified": updated_user.is_email_verified,
    }

    return Ok(data=response, message="Reset password successfully")


@router.post("/google-login")
async def google_login(
    auth_request: GoogleAuthRequest,
    student_controller: StudentController = Depends(InternalProvider().get_student_controller),
    professor_controller: ProfessorController = Depends(InternalProvider().get_professor_controller),
    admin_controller: AdminController = Depends(InternalProvider().get_admin_controller),
):
    role = await check_exist_and_get_role_for_user(auth_request.user_info.email, student_controller=student_controller, professor_controller=professor_controller, admin_controller=admin_controller)

    user = None
    role_response = None

    if role == "professor":
        user = await professor_controller.professor_repository.first(
            where_=[Professor.email == auth_request.user_info.email]
        )
        role_response = "professor"
    elif role == "admin":
        user = await admin_controller.admin_repository.first(where_=[Admin.email == auth_request.user_info.email])
        role_response = "admin"
    else:
        user = await student_controller.student_repository.first(where_=[Student.email == auth_request.user_info.email])
        role_response = "student"

    if user and user.password:
        user_response = {
            "name": user.name,
            "email": user.email,
            "is_email_verified": user.is_email_verified,
            "role": role_response,
        }
        return Ok(
            data=create_tokens_response(user.id, user_response),
            message="Login successfully",
        )

    if user and not user.password:
        user_response = {
            "name": user.name,
            "email": user.email,
            "is_email_verified": user.is_email_verified,
        }
        return Ok(
            data=user_response,
            message="Your account hasn't had the password. Please add a password to your account to complete your profile.",
        )

    user_attributes = {
        "name": auth_request.user_info.name,
        "email": auth_request.user_info.email,
        "avatar_url": auth_request.user_info.picture,
        "is_email_verified": auth_request.user_info.verified_email,
        "is_active": True,
    }

    if role == "professor":
        new_user = await professor_controller.professor_repository.create(attributes=user_attributes, commit=True)
    elif role == "admin":
        new_user = await admin_controller.admin_repository.create(attributes=user_attributes, commit=True)
    else:
        new_user = await student_controller.student_repository.create(attributes=user_attributes, commit=True)

    if not new_user:
        raise Exception("Cannot create user. Please contact the admin for support")

    user_response = {
        "name": new_user.name,
        "email": new_user.email,
    }

    return Ok(
        data=user_response,
        message="Google login successfully! Please add password to your account to complete your profile.",
    )
