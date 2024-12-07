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
    isSuccess: bool = True
    errorCode: int = 0
    message: str = "Operation successful"
    messageCode: str = "SUCCESS"

    def __init__(self, data: T, **kwargs):
        super().__init__(data=data, **kwargs)


class Error(BaseResponse[None]):
    isSuccess: bool = False
    errorCode: int
    message: str
    messageCode: str = "ERROR"

    def __init__(self, error_code: int, message: str, **kwargs):
        super().__init__(errorCode=error_code, message=message, **kwargs)
