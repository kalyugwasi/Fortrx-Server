from sqlalchemy.orm import Session
from fastapi import HTTPException,status
from app.repositories import message_repo,user_repo
from app.schemas import MessageSend
from app.services import generate_blob_key,upload_blob,download_blob,delete_blob
from app.services.connection_manager import manager
import asyncio,websockets,base64
from datetime import datetime,timedelta,timezone

async def send_message(db:Session,sender_id:int,payload:MessageSend):
    recipient = user_repo.get_user_by_id(db,payload.recipient_id)
    if not recipient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Recipient not found")
    blob_key = generate_blob_key(payload.recipient_id)
    raw = base64.b64decode(payload.sealed_blob)
    upload_blob(blob_key,raw)

    if payload.ttl_seconds is not None:
        expires_at = datetime.utcnow().replace(microsecond=0) + timedelta(seconds=payload.ttl_seconds)
    else:
        expires_at = None
        
    message = message_repo.save_message(
        db=db,
        recipient_id=payload.recipient_id,
        message_number=payload.message_number,
        sealed_blob=blob_key,
        expires_at = expires_at
    )
    
    await manager.send_to_user(
            payload.recipient_id,{
                "type":"new_message",
                "message_id":message.id,
                #"blob_key":blob_key,
                "message_number":payload.message_number,
                "expires_at":expires_at.isoformat() if expires_at else None
            }
        )
    return message

def fetch_inbox(db:Session,user_id:int):
    messages = message_repo.get_message_for_user(db,user_id)
    for msg in messages:
        raw = download_blob(msg.sealed_blob)
        msg.sealed_blob = base64.b64encode(raw).decode()
    return messages
        

def confirm_delivery(db:Session,message_id:int,user_id:int):
    message = db.query(message_repo.Message).filter(message_repo.Message.id==message_id).first()
    if not message:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="Message not found")
    
    if message.recipient_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="Not allowed")
    
    delete_blob(message_repo.Message.sealed_blob)
    
    message_repo.delete_message(db,message_id)
    return {"message":"deleted"}

def purge_expired_messages(db):
    from app.models import Message
    from datetime import datetime

    now = datetime.utcnow().replace(microsecond=0)

    deleted = (
        db.query(Message)
        .filter(Message.expires_at.isnot(None))
        .filter(Message.expires_at <= now)
        .delete(synchronize_session=False)
    )

    db.commit()

    return deleted