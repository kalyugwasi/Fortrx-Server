from jose import jwt
from jose.exceptions import JWTError
from datetime import datetime,timedelta
from app.config import settings

def create_access_token(data:dict)->str:
    to_encode = data.copy()
    expire = datetime.utcnow().replace(microsecond=0) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode["exp"] = expire
    return jwt.encode(to_encode,settings.SECRET_KEY,algorithm=settings.ALGORITHM)

def decode_access_token(token:str)->dict|None:
    try:
        payload = jwt.decode(token,settings.SECRET_KEY,algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None
    
def create_token_for_user(user_id:int,username:str)->str:
    return create_access_token({
        "sub":str(user_id),
        "username":username
        })
    