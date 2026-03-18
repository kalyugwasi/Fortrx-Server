from pydantic import BaseModel
from typing import Optional,List

class KeyBundleUpload(BaseModel):
    identity_key:str
    signed_prekey:str
    signed_prekey_signature:str
    prekey_id:int
    one_time_prekeys:List[str]
    
class KeyBundleResponse(BaseModel):
    user_id:int
    identity_key:str
    signed_prekey:str
    signed_prekey_signature:str
    prekey_id:int
    one_time_prekey:Optional[str]
    
    class Config():
        from_attributes = True