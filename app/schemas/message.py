from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class MessageSend(BaseModel):
    recipient_id:int
    sealed_blob:str
    message_number:int
    ttl_seconds:int | None = None
    
class MessageResponse(BaseModel):
    id:int
    recipient_id:int
    message_number:int
    sealed_blob:str
    created_at:datetime
    expires_at: Optional[datetime]
    
    class Config():
        from_attributes=True