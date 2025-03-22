from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from core.exceptions.base import BadRequestException, NotFoundException
from core.utils.auth_utils import verify_token
from machine.controllers.user import StudentController
from machine.models.student import Student
from machine.providers.internal import InternalProvider


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

async def get_current_student(
    token: str = Depends(oauth2_scheme),
    student_controller: StudentController = Depends(InternalProvider().get_student_controller),
) -> Student:
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")
    user = await student_controller.student_repository.first(where_=[Student.id == user_id])
    if not user:
        raise NotFoundException(message="Only Student have the permission to get this module.")
    return user
