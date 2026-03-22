from sqlalchemy.orm import Session
from fastapi import HTTPException,status
from app.repositories import message_repo,user_repo
from app.schemas import MessageSend
from app.services import generate_blob_key,upload_blob,download_blob,delete_blob

def send_message(db:Session,sender_id:int,payload:MessageSend):
    recipient = user_repo.get_user_by_id(db,payload.reciepient_id)
    if not recipient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Recipient not found")
    
    blob_key = generate_blob_key(sender_id,payload.reciepient_id)
    upload_blob(blob_key,payload.ciphertext.encode())

    return message_repo.save_message(
        db=db,
        sender_id=sender_id,
        recipient_id=payload.reciepient_id,
        header= payload.header,
        message_number=payload.message_number,
        blob_key=blob_key
    )

def fetch_inbox(db:Session,user_id:int):
    messages = message_repo.get_message_for_user(db,user_id)
    for msg in messages:
        raw = download_blob(msg.blob_key)
        msg.ciphertext = raw.decode()
    return messages
        

def fetch_conversation(db:Session,user_a:int,user_b:int):
    return message_repo.get_conversation(db,user_a,user_b)

def confirm_delivery(db:Session,message_id:int,user_id:int):
    message = db.query(message_repo.Message).filter(message_repo.Message.id==message_id).first()
    if not message:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="Message not found")
    
    if message.recipient_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="Not allowed")
    
    delete_blob(message_repo.Message.blob_key)
    
    message_repo.delete_message(db,message_id)
    return {"message":"delivered"}