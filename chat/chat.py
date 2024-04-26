import base64
import hashlib
import json

from typing import List, Dict

from sqlalchemy import insert, select

from models.models import Message, Users, Room
from .scheme import MessageScheme, ReceiverScheme, MessageShowScheme
from auth.schemas import UserInfo
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from auth.utils import verify_token
from database import get_async_session
from starlette import status
from starlette.websockets import WebSocketDisconnect
from fastapi import WebSocket, APIRouter, Depends
from fastapi.exceptions import HTTPException

chat_router = APIRouter()


class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket, room: str):
        if len(self.active_connections) < 2:
            await websocket.accept()
            self.active_connections.append({"socket": websocket, "room": room})

    async def disconnect(self, websocket: WebSocket):
        for connection in self.active_connections:
            if connection["socket"] == websocket:
                self.active_connections.remove(connection)
                break

    async def broadcast(self, message: str, room: str):
        for connection in self.active_connections:
            if connection["room"] == room:
                await connection["socket"].send_text(message)


manager = WebSocketManager()


@chat_router.websocket("/ws/{room}")
async def websocket_endpoint(websocket: WebSocket, room: str):
    await manager.connect(websocket, room)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(data, room)
    except WebSocketDisconnect:
        await manager.disconnect(websocket)


@chat_router.post("/ws/send-file")
async def send_file(file_data: bytes, room: str):
    base64_data = base64.b64encode(file_data).decode("utf-8")
    await manager.broadcast(base64_data, room)
    return {"message": "File sent"}


@chat_router.post("/ws/send-message")
async def send_message(
    message: MessageScheme,
    token: dict = Depends(verify_token),
    session: AsyncSession = Depends(get_async_session),
):
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Token not provided"
        )
    try:
        sender_id = token.get("user_id")
        message_text = message.message
        print(message_text)
        receiver_id = message.receiver
        query = insert(Message).values(
            sender_id=sender_id,
            receiver_id=receiver_id,
            message=message_text,
        )
        await session.execute(query)
        await session.commit()
        return {"success": True}
    except Exception as e:
        print(str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@chat_router.get("/ws/get-users", response_model=List[UserInfo])
async def get_users(
    token: dict = Depends(verify_token),
    session: AsyncSession = Depends(get_async_session),
):
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Token not provided"
        )
    user_id = token.get("user_id")
    try:
        query = select(Users).where(Users.id != user_id)
        user__data = await session.execute(query)
        user_datas = user__data.scalars().all()
        return user_datas
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@chat_router.post("/ws/room", response_model=None)
async def get_or_create_room(
    receiver: ReceiverScheme,
    token: dict = Depends(verify_token),
    session: AsyncSession = Depends(get_async_session),
):
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Token not provided"
        )
    sender_id = token.get("user_id")
    try:
        room_data = {"sender_id": sender_id, "receiver_id": receiver.receiver_id}
        dump_data = json.dumps(room_data)
        hash_object = hashlib.sha256(dump_data.encode())
        unique_code = hash_object.hexdigest()
        query_get = select(Room).where(
            ((Room.sender_id == sender_id) & (Room.receiver_id == receiver.receiver_id))
            | (
                (Room.sender_id == receiver.receiver_id)
                & (Room.receiver_id == sender_id)
            )
        )
        room_data = await session.execute(query_get)
        try:
            result = room_data.scalars().one()
        except NoResultFound:
            try:
                query = insert(Room).values(
                    key=unique_code,
                    sender_id=sender_id,
                    receiver_id=receiver.receiver_id,
                )
                await session.execute(query)
                await session.commit()

                result_query = select(Room).where(Room.key == unique_code)
                result_data = await session.execute(result_query)
                result = result_data.scalars().one()
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
                )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return result


@chat_router.post("/ws/messages", response_model=List[MessageShowScheme])
async def get_chat_messages(
    receiver_id: int,
    token: dict = Depends(verify_token),
    session: AsyncSession = Depends(get_async_session),
):
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Token not provided"
        )
    try:
        sender_id = token.get("user_id")
        query = select(Message).where(
            ((Message.sender_id == sender_id) & (Message.receiver_id == receiver_id))
            | ((Message.sender_id == receiver_id) & (Message.receiver_id == sender_id))
        )
        message_data = await session.execute(query)
        result = message_data.scalars().all()
        return result
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
