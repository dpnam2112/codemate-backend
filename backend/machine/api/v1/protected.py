import os
import jwt
from jwt import PyJWTError
from datetime import datetime
from dotenv import load_dotenv
from fastapi.security import OAuth2PasswordBearer
from fastapi import APIRouter, Depends, HTTPException, Header
from datetime import datetime, timedelta, timezone

load_dotenv()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

router = APIRouter(prefix="/auth", tags=["auth"])
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")


def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        exp = payload.get("exp")
        current_time = int(datetime.now(timezone(timedelta(hours=7))).timestamp())

        if exp is None:
            raise HTTPException(status_code=401, detail="Token has no expiration")

        if current_time > exp:
            raise HTTPException(status_code=401, detail="Token has expired")

        return payload

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except PyJWTError as e:  
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


@router.get("/protected")
async def protected_route(token: str = Depends(oauth2_scheme)):
    """
    Test Protected Route with Bearer Token
    This endpoint is protected, so only users with valid tokens can access it.
    """
    payload = verify_token(token)

    return {"message": "Token is valid", "user_info": payload}
