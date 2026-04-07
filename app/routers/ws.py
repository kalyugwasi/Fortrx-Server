import asyncio
import json
import uuid

from fastapi import APIRouter,WebSocket,WebSocketDisconnect,Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.crypto import decode_access_token
from app.services import manager,subscribe_to_user,unsubscribe_from_user
from app.services import presence_service

router = APIRouter(tags=["websocket"])


def _extract_bearer_token(websocket: WebSocket) -> str | None:
    auth_header = websocket.headers.get("authorization")
    if not auth_header:
        return None
    scheme, _, token = auth_header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token.strip()

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(
    user_id:int,
    websocket: WebSocket,
    db: Session = Depends(get_db)
):
    token = _extract_bearer_token(websocket)
    if not token:
        await websocket.close(code=1008)
        return
    payload = decode_access_token(token)
    if not payload:
        await websocket.close(code=1008)
        return
    try:
        token_user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        await websocket.close(code=1008)
        return
    if token_user_id!=user_id:
        await websocket.close(code=1008)
        return
    session_id = f"ws:{uuid.uuid4().hex}"
    await manager.connect(user_id,websocket)
    await presence_service.heartbeat_and_broadcast(db, user_id, session_id)
    pubsub,r = await subscribe_to_user(user_id)
    
    async def client_listener():
        try:
            while True:
                text = await websocket.receive_text()
                if text == "ping":
                    await websocket.send_text("pong")
                    await presence_service.heartbeat_and_broadcast(db, user_id, session_id)
        except WebSocketDisconnect:
            pass
    
    async def redis_listener():
        try:
            async for message in pubsub.listen():
                if message and message.get("type") == "message":
                    data = json.loads(message.get("data", "{}"))
                    await websocket.send_json(data)
        except Exception:
            pass
    
    redis_task = asyncio.create_task(client_listener())
    ws_task = asyncio.create_task(redis_listener())
    
    done,pending = await asyncio.wait(
        [redis_task,ws_task],
        return_when=asyncio.FIRST_COMPLETED
    )
    for task in pending:
        task.cancel()
    manager.disconnect(user_id, websocket)
    await unsubscribe_from_user(pubsub,r)
    await presence_service.disconnect_and_broadcast(db, user_id, session_id)
