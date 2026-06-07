from fastapi import WebSocket
from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Message, User
from app.service.users import get_user_model


class ConnectionManager:
    def __init__(self):
        self.connections: dict[int, list[WebSocket]] = {}

    async def connect(self, user_id: int, websocket: WebSocket):
        self.connections.setdefault(user_id, []).append(websocket)

    def disconnect(self, user_id: int, websocket: WebSocket):
        if user_id in self.connections:
            try:
                self.connections[user_id].remove(websocket)
            except ValueError:
                pass

            if not self.connections[user_id]:
                self.connections.pop(user_id)


    async def send_to_user(self, user_id: int, message: dict):
        websockets = list(self.connections.get(user_id, []))
        for websocket in websockets:
            try:
                await websocket.send_json(message)
            except Exception:
                self.disconnect(user_id, websocket)

    def is_online(self, user_id: int) -> bool:
        return user_id in self.connections


manager = ConnectionManager()


async def save_message(db: AsyncSession, sender_id: int, receiver_id: int, text: str) -> Message:
    existing_receiver = await get_user_model(db, sender_id)

    if not existing_receiver:
        raise Exception(f"User {sender_id} doesn't exist")

    message = Message(sender_id=sender_id, receiver_id=receiver_id, text=text)
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return message


async def get_chat_history(db: AsyncSession, user_id: int, other_user_id: int) -> list[Message]:
    result = await db.execute(
        select(Message)
        .where(or_(
            and_(Message.sender_id == user_id, Message.receiver_id == other_user_id),
            and_(Message.sender_id == other_user_id, Message.receiver_id == user_id),
        ))
        .order_by(Message.id)
    )
    return result.scalars().all()
