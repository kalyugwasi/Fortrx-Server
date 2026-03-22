from sqlalchemy.orm import Session
from fastapi import HTTPException,status
from app.repositories import message_repo,user_repo
from app.schemas import MessageSend

def send_message(db:Session,sender_id:int,payload:MessageSend):
    recipient = user_repo.get_user_by_id(db,payload.reciepient_id)
    if not recipient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Recipient not found")
    
    return message_repo.save_message(
        db=db,
        sender_id=sender_id,
        recipient_id=payload.reciepient_id,
        ciphertext=payload.ciphertext,
        header= payload.header,
        message_number=payload.message_number
    )

def fetch_inbox(db:Session,user_id:int):
    return message_repo.get_message_for_user(db,user_id)

def fetch_conversation(db:Session,user_a:int,user_b:int):
    return message_repo.get_conversation(db,user_a,user_b)

def confirm_delivery(db:Session,message_id:int,user_id:int):
    message = db.query(message_repo.Message).filter(message_repo.Message.id==message_id).first()
    if not message:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="Message not found")
    
    if message.recipient_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="Not allowed")
    
    message_repo.delete_message(db,message_id)
    return {"message":"delivered"}