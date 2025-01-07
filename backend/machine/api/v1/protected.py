from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordBearer
from core.utils.auth_utils import verify_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

router = APIRouter(prefix="/auth", tags=["auth"])

@router.get("/protected")
async def protected_route(token: str = Depends(oauth2_scheme)):
    """
    Test Protected Route with Bearer Token
    This endpoint is protected, so only users with valid tokens can access it.
    Example of payload:
    {
    "message": "Token is valid",
    "user_info": {
        "sub": "8fb9b551-d176-4966-bc6b-f52fdfca14c7" => This is the id of the user, 
        "exp": 1736269971
        }
    }
    """
    
    
    payload = verify_token(token)
    return {"message": "Token is valid", "user_info": payload}
