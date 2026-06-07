from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from jose import jwt, JWTError
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import get_db, db_dependency
from app.schemas.chat import IncomingMessage
from app.service.chat import manager, save_message, get_chat_history
from app.service.auth import get_current_user
from app.db.models import User

router = APIRouter(prefix="/api/v1/chat",tags=["Chat"])


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, db: AsyncSession = Depends(get_db)):
    await websocket.accept()
    auth_data = await websocket.receive_json()
    token = auth_data.get("token")

    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id_str = payload.get("sub")
        if user_id_str is None:
            await websocket.close(code=1008)
            return
        user_id = int(user_id_str)
    except JWTError:
        await websocket.close(code=1008)
        return

    await manager.connect(user_id, websocket)

    try:
        while True:
            data = await websocket.receive_json()

            try:
                msg = IncomingMessage(**data)
            except ValidationError:
                await manager.send_to_user(user_id, {"error": "invalid message"})
                continue

            receiver = await db.get(User, msg.receiver_id)

            if receiver is None:
                await manager.send_to_user(user_id, {"error": "user not found"})
                continue

            message = await save_message(db, user_id, msg.receiver_id, msg.text)

            payload = {
                "id": message.id,
                "sender_id": user_id,
                "receiver_id": msg.receiver_id,
                "text": msg.text,
                "created_at": message.created_at.isoformat(),
            }

            await manager.send_to_user(msg.receiver_id, payload)
            await manager.send_to_user(user_id, payload)

    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)


@router.get("/history/{other_user_id}")
async def chat_history(other_user_id: int, db: db_dependency, curr_user: User = Depends(get_current_user)):
    messages = await get_chat_history(db, curr_user.id, other_user_id)
    return messages