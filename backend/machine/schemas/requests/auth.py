from pydantic import BaseModel

class LoginRequest(BaseModel):
    email: str
    password: str
    
class VerifyEmailRequest(BaseModel):
    email: str
    code: str
    
class ResendVerificationCodeRequest(BaseModel):
    email: str
    
class ForgotPasswordRequest(ResendVerificationCodeRequest):
    pass 

class ResetPasswordRequest(BaseModel):
    email: str
    code: str
    new_password: str
    
class UserInformationFromGoogle(BaseModel):
  id: str
  email: str
  verified_email: bool
  name: str
  given_name: str
  family_name: str
  picture: str
class GoogleAuthRequest(BaseModel):
    access_token: str
    user_info: UserInformationFromGoogle