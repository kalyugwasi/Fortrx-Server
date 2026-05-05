from pydantic import BaseModel


class ReauthRequest(BaseModel):
    password: str


class ReauthResponse(BaseModel):
    reauth_token: str
    expires_at: int


class ResetPasswordRequest(BaseModel):
    password: str
