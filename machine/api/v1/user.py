from typing import List, Union

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

    


# @router.post("/", response_model=Union[UserResponse, List[UserResponse]])
# async def create(
#     body: Union[UserRequest, List[UserRequest]],
#     bulk: bool = Query(False, description="Whether to create a bulk of users"),
#     user_controller: UserController = Depends(InternalProvider().get_user_controller),
# ):
#     """
#     Create user(s)
#     """
#     if bulk:
#         if not isinstance(body, List):
#             raise BadRequestException("Body must be a list when bulk is True")
#         created_users = await user_controller.create_many([user.model_dump() for user in body])
#         return created_users
#     else:
#         if isinstance(body, List):
#             raise BadRequestException("Body must be a single user when bulk is False")
#         created_user = await user_controller.create(body.model_dump())
#         return created_user


# # @router.post("/upsert")
# # async def upsert(
# #     body: Union[UserRequest, List[UserRequest]],
# #     bulk: bool = Query(False, description="Whether to upsert a bulk of users"),
# #     user_controller: UserController = Depends(InternalProvider().get_user_controller),
# # ):
# #     """
# #     Upsert user(s)
# #     """
# #     if bulk:
# #         if not isinstance(body, List):
# #             raise BadRequestException("Body must be a list when bulk is True")
# #         created_users = await user_controller.upsert_many(index_elements=["id"], attributes_list=[user.model_dump() for user in body])
# #         return created_users
# #     else:
# #         if isinstance(body, List):
# #             raise BadRequestException("Body must be a single user when bulk is False")
# #         created_user = await user_controller.upsert(index_elements=["id"], attributes=body.model_dump())
# #         return created_user


# # @router.get("/")
# # async def list(
# #     user_controller: UserController = Depends(InternalProvider().get_user_controller),
# # ):
# #     """
# #     List all users
# #     """
# #     users = await user_controller.get_many(distinct=[User.name])
# #     return users


# # @router.delete("/{id}")
# # async def delete(
# #     id: int,
# #     user_controller: UserController = Depends(InternalProvider().get_user_controller),
# # ):
# #     """
# #     Delete a user
# #     """
# #     return await user_controller.delete(where_=[User.id == id])
