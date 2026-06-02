from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db, db_dependency
from app.service.chat import manager, save_message, get_chat_history
from app.service.auth import get_current_user, SECRET_KEY, ALGORITHM
from app.db.models import User

router = APIRouter(prefix="/api/v1/chat",tags=["Chat"])


@router.websocket("/test")
async def websocket_test(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_text("работает!")
    await websocket.close()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, db: AsyncSession = Depends(get_db)):
    await websocket.accept()
    auth_data = await websocket.receive_json()
    token = auth_data.get("token")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
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
            receiver_id = data.get("receiver_id")
            text = data.get("text")

            if not receiver_id or not text:
                continue

            # сохраняем в базу
            message = await save_message(db, user_id, receiver_id, text)

            # формируем ответ
            payload = {
                "id": message.id,
                "sender_id": user_id,
                "receiver_id": receiver_id,
                "text": text,
                "created_at": message.created_at.isoformat(),
            }

            # отправляем получателю если онлайн
            await manager.send_to_user(receiver_id, payload)

            # отправляем подтверждение отправителю
            await manager.send_to_user(user_id, payload)

    except WebSocketDisconnect:
        manager.disconnect(user_id)


@router.get("/history/{other_user_id}")
async def chat_history(other_user_id: int, db: db_dependency, curr_user: User = Depends(get_current_user)):
    messages = await get_chat_history(db, curr_user.id, other_user_id)
    return messages