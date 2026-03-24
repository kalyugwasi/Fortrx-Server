from sqlalchemy.orm import Session
from app.models import Message
from datetime import datetime

def save_message(db:Session,recipient_id,message_number,sealed_blob,expires_at=None):
    message = Message(
        recipient_id=recipient_id,
        sealed_blob=sealed_blob,
        message_number=message_number,
        expires_at = expires_at
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message

def get_message_for_user(db:Session,user_id:int):
    return (
        db.query(Message)
        .filter(Message.recipient_id==user_id)
        .order_by(Message.created_at.asc())
        .all()
    )

def delete_message(db:Session,message_id:int):
    message = db.query(Message).filter(Message.id == message_id).first()
    if message:
        db.delete(message)
        db.commit()
    return message

def purge_expired_messages(db: Session):
    now = datetime.utcnow()

    deleted = (
        db.query(Message)
        .filter(Message.expires_at.isnot(None))
        .filter(Message.expires_at <= now)   # ✅ critical fix
        .delete(synchronize_session=False)   # ✅ critical fix
    )

    db.commit()
    return deleted