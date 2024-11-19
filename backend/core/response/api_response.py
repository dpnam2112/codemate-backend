from typing import Generic, Optional, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class BaseResponse(BaseModel, Generic[T]):
    isSuccess: bool
    errorCode: int
    message: str
    messageCode: str
    data: Optional[T] = None


class Ok(BaseResponse[T]):
    def __init__(self, data: T, message: str = "Operation successful", message_code: str = "SUCCESS"):
        super().__init__(
            isSuccess=True,
            errorCode=0,
            message=message,
            messageCode=message_code,
            data=data
        )


class Error(BaseResponse[None]):
    def __init__(self, error_code: int, message: str, message_code: str = "ERROR"):
        super().__init__(
            isSuccess=False,
            errorCode=error_code,
            message=message,
            messageCode=message_code,
            data=None
        )
