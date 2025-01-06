import os
import jwt
import random
import string
import secrets
from fastapi import Depends
from core.response import Ok
from fastapi import APIRouter
from dotenv import load_dotenv
from core.utils.email import conf
from machine.models import Student
from datetime import datetime, timedelta
from passlib.context import CryptContext
from utils.functions import validate_email
from machine.providers import InternalProvider
from fastapi_mail import FastMail, MessageSchema
from core.exceptions import *
from machine.controllers import StudentController
from machine.schemas.requests.auth import *

load_dotenv()
secret_key = secrets.token_urlsafe(32)
SECRET_KEY = os.getenv("SECRET_KEY", secret_key) 
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30)) 

fm = FastMail(conf)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter(prefix="/auth", tags=["auth"])

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)  # Mặc định là 15 phút nếu không cung cấp
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Hàm gửi email xác thực
async def send_email_to_user(email: str, code: str):
    message = MessageSchema(
        subject="Mã xác thực của bạn", recipients=[email], body=f"Đây là mã xác thực của bạn: {code}", subtype="plain"
    )
    await fm.send_message(message)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def generate_code(length: int = 6) -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))

@router.post("/login")
async def login(
    request: LoginRequest,
    student_controller: StudentController = Depends(InternalProvider().get_student_controller),
):
    """
    Login User
    """
    if not request.email or not request.password:
        return UnauthorizedException("Email and password are required.")
    if not validate_email(request.email):
        return UnauthorizedException("Invalid email")
    
    user = await student_controller.student_repository.first(where_=[Student.email == request.email])
    
    if not user and not user.verification_code:
        # If user doesn't exist, send a verification code to email
        code = generate_code()
        await send_email_to_user(request.email, code)

        # Modify student attributes directly in the API
        student_attributes = {
            "name": request.email.split("@")[0],  # Default name based on email
            "email": request.email,
            "password": hash_password(request.password),
            "verification_code": code,
            "verification_code_expires_at": datetime.utcnow() + timedelta(minutes=10),
            "is_email_verified": False,  # Newly created user is not verified
        }

        # Create new user (using the repository's `create` method)
        new_student = await student_controller.student_repository.create(attributes=student_attributes, commit=True)
        
        # Map new student data into a response structure similar to the `StudentOut`
        student_response = {
            "id": new_student.id,
            "name": new_student.name,
            "email": new_student.email,
            "is_email_verified": new_student.is_email_verified,
            "verification_code": new_student.verification_code,
            "verification_code_expires_at": new_student.verification_code_expires_at,
        }
        
        # Return the response
        return Ok(
            data=student_response, 
            message="User not found. Verification code sent to email"
        )
        
    elif not user and user.verification_code:
        return UnauthorizedException("User not found. Please check your email for verification code")
    
    if not pwd_context.verify(request.password, user.password):
        return UnauthorizedException("Invalid password")
    
    if not user.is_email_verified:
        return UnauthorizedException("Email is not verified. Please verify your email.")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )

    # Return successful login response
    user_response = {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "is_email_verified": user.is_email_verified,
    }

    return Ok(
        data={"access_token": access_token, "token_type": "bearer", **user_response},
        message="Login successfully"
    )

@router.post("/verify-email")
async def verify_email(
    request: VerifyEmailRequest,
    student_controller: StudentController = Depends(InternalProvider().get_student_controller),
):
    """
    Verify Email Address
    """
    # Tìm người dùng theo email
    if not request.email or not request.code:
        raise UnauthorizedException("Email and code are required")
    
    user = student_controller.get_user_by_email(request.email)
    
    if not user:
        raise NotFoundException("User not found")

    # Kiểm tra mã xác thực
    if request.code != user.verification_code:
        raise UnauthorizedException("Invalid verification code")

    # Kiểm tra mã có hết hạn chưa
    if user.verification_code_expires_at < datetime.utcnow():
        raise UnauthorizedException("Verification code has expired")

    # Cập nhật trạng thái xác thực email
    user.is_email_verified = True
    user.verification_code = None  # Xóa mã xác thực
    user.verification_code_expires_at = None  # Xóa thời gian hết hạn
    #use the update method to update the user
    updateUserInfor = await student_controller.student_repository.update(model=user, commit=True)

    return Ok(data=updateUserInfor, message="Email verified successfully")
