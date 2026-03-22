from fastapi import APIRouter,Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_active_user
from app.schemas import MessageSend,MessageResponse
from app.models import User
from app.services import message_service

router = APIRouter(
    prefix="/messages",
    tags=["messages"]
)
@router.post("/send",response_model=MessageResponse,status_code=201)
def send_message(
    payload:MessageSend,
    db: Session= Depends(get_db),
    current_user: User = Depends(get_active_user)
):
    return message_service.send_message(db,current_user.id,payload)

@router.get("/inbox",response_model=list[MessageResponse])
def get_inbox(
    db:Session=Depends(get_db),
    current_user:User= Depends(get_active_user)
):
    return message_service.fetch_inbox(db,current_user.id)

@router.get("/conversation/{other_user_id}",response_model=list[MessageResponse])
def get_conversation(
    other_user_id:int,
    db:Session=Depends(get_db),
    current_user:User=Depends(get_active_user)
):
    return message_service.fetch_conversation(db,current_user.id,other_user_id)

@router.delete("/{message_id}/confirm")
def confirm_delivery(
    message_id:int,
    db:Session=Depends(get_db),
    current_user:User = Depends(get_active_user)
):
    return message_service.confirm_delivery(db,message_id,current_user.id)