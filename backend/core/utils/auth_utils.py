import os
import jwt
from jwt import PyJWTError
from datetime import datetime, timezone, timedelta
from core.exceptions import UnauthorizedException

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        exp = payload.get("exp")
        current_time = int(datetime.now(timezone(timedelta(hours=7))).timestamp())

        if exp is None:
            raise UnauthorizedException("Token is invalid")

        if current_time > exp:
            raise UnauthorizedException("Token has expired")

        return payload

    except jwt.ExpiredSignatureError:
        raise UnauthorizedException("Token has expired")
    except PyJWTError as e:  
        raise UnauthorizedException("Token is invalid", e)
