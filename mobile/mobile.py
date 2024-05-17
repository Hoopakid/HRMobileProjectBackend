import os
import aiofiles

from starlette import status

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, UploadFile, Request
from fastapi.templating import Jinja2Templates
from fastapi.exceptions import HTTPException
from sqlalchemy import select, update, delete, insert
from fastapi.responses import HTMLResponse
from models.models import Users, Tasks, Degree
from auth.utils import verify_token
from database import get_async_session
from models.models import UserMessagesToAdminViaTask, SupportForUser

templates = Jinja2Templates(directory="templates")

mobile_router = APIRouter()


@mobile_router.get(
    "/dashboard-api",
)
async def get_data(
    session: AsyncSession = Depends(get_async_session),
):
    tasks_data = select(Tasks)
    tasks__data = await session.execute(tasks_data)
    tasks = tasks__data.scalars().all()

    degree_data = select(Degree)
    degree__data = await session.execute(degree_data)
    degrees = degree__data.scalars().all()
    ctx = {}
    for i in degrees:
        ctx.update({i.degree: 0})

    for task in tasks:
        degree_id = task.degree
        degree_one = select(Degree).where(Degree.id == degree_id)
        degree__one = await session.execute(degree_one)
        degree_one = degree__one.scalars().one()
        ctx[degree_one.degree] += 1

    return ctx


@mobile_router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@mobile_router.get("/get-tasks")
async def get_tasks(
    token: dict = Depends(verify_token),
    session: AsyncSession = Depends(get_async_session),
):
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Token not provided"
        )

    user_id = token.get("user_id")
    user_existing_query = select(Users).where(Users.id == user_id)
    user__data = await session.execute(user_existing_query)
    user_data = user__data.scalars().one_or_none()
    if user_data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found that given id",
        )
    try:
        user_degree_id = user_data.degree
        get_tasks_by_section = select(Tasks).where(
            (Tasks.user == user_id)
            | (Tasks.degree == user_degree_id if user_degree_id is not None else 0)
        )
        tasks__data = await session.execute(get_tasks_by_section)
        tasks = tasks__data.scalars().all()

        users = select(Users)
        users__data = await session.execute(users)
        users_dict = {user.id: user for user in users__data.scalars().all()}
        for task in tasks:
            user = task.user
            if user in users_dict:
                user_data = users_dict[user]
                user_dict = {
                    key: getattr(user_data, key)
                    for key in user_data.__dict__.keys()
                    if key != "password"
                }
                task.user = user_dict
        return tasks
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@mobile_router.get("/get-filtered-tasks")
async def get_filtered_tasks(
    token: dict = Depends(verify_token),
    session: AsyncSession = Depends(get_async_session),
):
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Token not provided"
        )
    user_id = token.get("user_id")
    user_existing_query = select(Users).where(Users.id == user_id)
    user__ = await session.execute(user_existing_query)
    user_ = user__.scalars().one_or_none()
    if user_ is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    try:
        task = select(Tasks)
        tasks__data = await session.execute(task)
        tasks = tasks__data.scalars().all()
        ctx = [{"NotCompleted": [], "InProgress": [], "Completed": []}]

        users = select(Users)
        users__data = await session.execute(users)
        users_dict = {user.id: user for user in users__data.scalars().all()}
        for task in tasks:
            user = task.user
            if user in users_dict:
                user_data = users_dict[user]
                user_dict = {
                    key: getattr(user_data, key)
                    for key in user_data.__dict__.keys()
                    if key != "password"
                }
                task.user = user_dict
            if task.status == "Yakunlangan":
                ctx[0]["Completed"].append(task)
            elif task.status == "Bajarilayotgan":
                ctx[0]["InProgress"].append(task)
            elif task.status == "Yakunlanmagan":
                ctx[0]["NotCompleted"].append(task)

        return ctx
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@mobile_router.patch("/start-the-task")
async def start_the_task(
    task_id: int,
    token: dict = Depends(verify_token),
    session: AsyncSession = Depends(get_async_session),
):
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Token not provided"
        )
    user_id = token.get("user_id")
    user_existing_query = select(Users).where(Users.id == user_id)
    user__ = await session.execute(user_existing_query)
    user_ = user__.scalars().one_or_none()
    if user_ is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    task_existing_query = select(Tasks).where(
        (Tasks.id == task_id)
        & (Tasks.user == user_id)
        & (Tasks.status == "Yakunlanmagan")
    )
    task__data = await session.execute(task_existing_query)
    task_data = task__data.scalars().one_or_none()
    if task_data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found that given id",
        )
    try:
        task_data.status = "Bajarilayotgan"

        user_dict = {
            key: getattr(task_data, key)
            for key in task_data.__dict__.keys()
            if key != "password"
        }
        await session.commit()
        await session.close()
        task_data.user = user_dict
        return task_data
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@mobile_router.patch("/complete-the-task")
async def complete_the_task(
    task_id: int,
    token: dict = Depends(verify_token),
    session: AsyncSession = Depends(get_async_session),
):
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Token not provided"
        )
    user_id = token.get("user_id")
    user_existing = select(Users).where(Users.id == user_id)
    user__ = await session.execute(user_existing)
    user_ = user__.scalars().one()
    if user_ is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    task_existing_query = select(Tasks).where(
        (Tasks.id == task_id)
        & (Tasks.user == user_id)
        & (Tasks.status == "Bajarilayotgan")
    )
    task__data = await session.execute(task_existing_query)
    task_data = task__data.scalars().one_or_none()
    if task_data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task or user not found that given id",
        )
    try:
        task_data.status = "Yakunlangan"
        user_dict = {
            key: getattr(task_data, key)
            for key in task_data.__dict__.keys()
            if key != "password"
        }
        await session.commit()
        await session.close()
        task_data.user = user_dict
        return task_data
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@mobile_router.post("/send-message-to-admin")
async def send_message_to_admin(
    task_id: int,
    message: str = None,
    voice: UploadFile = None,
    token: dict = Depends(verify_token),
    session: AsyncSession = Depends(get_async_session),
):
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Token not provided"
        )
    user_id = token.get("user_id")
    checking_user = select(Users).where((Users.id == user_id) & (Users.status == False))
    user__data = await session.execute(checking_user)
    user = user__data.scalars().one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in the base or you have not access to send message to admin",
        )
    if message and voice:
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail="You cannot send both at the same time",
        )
    checking_task = select(Tasks).where(Tasks.id == task_id)
    task__data = await session.execute(checking_task)
    task = task__data.scalars().one_or_none()
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found that given id",
        )
    try:
        get_admin = select(Users).where(Users.status == True)
        admin__data = await session.execute(get_admin)
        admin_data = admin__data.scalars().one_or_none()
        if admin_data is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sorry, this error from database, please try again",
            )
        if message is not None:
            message_create = insert(UserMessagesToAdminViaTask).values(
                sender_id=user_id,
                message=message,
                task_id=task_id,
                receiver_id=admin_data.id,
            )
            await session.execute(message_create)
        elif voice is not None:
            if (
                not voice.filename.endswith(".wav")
                or not voice.filename.endswith(".mp3")
                or not voice.filename.endswith("ogg")
            ):
                raise HTTPException(
                    status_code=status.HTTP_406_NOT_ACCEPTABLE,
                    detail="You can send only format of audio files",
                )
            base_filename, file_extension = os.path.splitext(voice.filename)
            out_file = f"uploads/VoiceMessages/{voice.filename}"
            index = 1
            while os.path.exists(out_file):
                out_file = (
                    f"uploads/VoiceMessages/{base_filename}_{index}{file_extension}"
                )
                index += 1
            async with aiofiles.open(out_file, "wb") as f:
                content = await voice.read()
                await f.write(content)
            voice_create = insert(UserMessagesToAdminViaTask).values(
                sender_id=user_id,
                voice=str(out_file),
                task_id=task_id,
                receiver_id=admin_data.id,
            )
            await session.execute(voice_create)
        await session.commit()
        inserted_message = (
            select(UserMessagesToAdminViaTask)
            .where(UserMessagesToAdminViaTask.sender_id == user_id)
            .where(UserMessagesToAdminViaTask.task_id == task_id)
            .where(UserMessagesToAdminViaTask.receiver_id == admin_data.id)
            .order_by(UserMessagesToAdminViaTask.sent_at.desc())
        )
        inserted_message_data = await session.execute(inserted_message)
        inserted_message_result = inserted_message_data.scalars().first()
        user_data = select(Users).where(Users.id == inserted_message_result.sender_id)
        receiver_data = select(Users).where(
            Users.id == inserted_message_result.receiver_id
        )
        user__data = await session.execute(user_data)
        receiver__data = await session.execute(receiver_data)
        user_data = user__data.scalars().one()
        receiver_data = receiver__data.scalars().one()
        task_data = select(Tasks).where(Tasks.id == inserted_message_result.task_id)
        task__data = await session.execute(task_data)
        task = task__data.scalars().one()
        user_dict = {
            key: getattr(user_data, key)
            for key in user_data.__dict__.keys()
            if key != "password"
        }
        receiver_dict = {
            key: getattr(receiver_data, key)
            for key in receiver_data.__dict__.keys()
            if key != "password"
        }

        inserted_message_result.sender_id = user_dict
        inserted_message_result.receiver_id = receiver_dict
        inserted_message_result.task_id = task.__dict__

        return inserted_message_result

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@mobile_router.get("/get-messages")
async def get_messages(
    task_id: int,
    token: dict = Depends(verify_token),
    session: AsyncSession = Depends(get_async_session),
):
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Token not provided"
        )
    user_id = token.get("user_id")

    task_existing_query = select(Tasks).where(Tasks.id == task_id)
    task__data = await session.execute(task_existing_query)
    task_data = task__data.scalars().one_or_none()
    if not task_data:
        raise HTTPException(
            detail="Task not found that given id",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    try:
        get_data_from_messages = select(UserMessagesToAdminViaTask).where(
            (UserMessagesToAdminViaTask.task_id == task_id)
            & (UserMessagesToAdminViaTask.sender_id == user_id)
        )
        message__datas = await session.execute(get_data_from_messages)
        message_data = message__datas.scalars().all()
        if not message_data:
            return {
                "success": True,
                "detail": "There is no messages that sent to admin",
            }
        await session.close()
        return message_data
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@mobile_router.delete("/delete-message")
async def delete_message(
    message_id: int,
    task_id: int,
    token: dict = Depends(verify_token),
    session: AsyncSession = Depends(get_async_session),
):
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Token not provided"
        )
    task_existing_id = select(Tasks).where(Tasks.id == task_id)
    task__data = await session.execute(task_existing_id)
    task_data = task__data.scalars().one_or_none()
    if not task_data:
        raise HTTPException(
            detail="Task not found that given id",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    user_id = token.get("user_id")
    message_existing_id = select(UserMessagesToAdminViaTask).where(
        (UserMessagesToAdminViaTask.id == message_id)
        & (UserMessagesToAdminViaTask.task_id == task_id)
        & (UserMessagesToAdminViaTask.sender_id == user_id)
    )
    message__data = await session.execute(message_existing_id)
    message_data = message__data.scalars().one_or_none()
    if not message_data:
        raise HTTPException(
            detail="Message not found that given id",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    try:
        if message_data.voice is not None:
            out_file = message_data.voice
            if os.path.exists(out_file):
                os.remove(out_file)
        deleting_message = delete(UserMessagesToAdminViaTask).where(
            (UserMessagesToAdminViaTask.id == message_id)
            & (UserMessagesToAdminViaTask.task_id == task_id)
            & (UserMessagesToAdminViaTask.sender_id == user_id)
        )
        await session.execute(deleting_message)
        await session.commit()
        return {
            "success": True,
            "detail": "Message has been deleted successfully",
            "status": status.HTTP_204_NO_CONTENT,
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@mobile_router.post("/support-admin")
async def support_admin(
    message: str = None,
    voice: UploadFile = None,
    token: dict = Depends(verify_token),
    session: AsyncSession = Depends(get_async_session),
):
    if token is None:
        raise HTTPException(
            detail="Token not provided", status_code=status.HTTP_403_FORBIDDEN
        )
    if message and voice:
        raise HTTPException(
            detail="You cannot send both at the same time",
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
        )
    user_id = token.get("user_id")
    checking_user = select(Users).where(Users.id == user_id)
    user__data = await session.execute(checking_user)
    user_data = user__data.scalars().one_or_none()
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    get_admin_id = select(Users).where(Users.status == True)
    admin__data = await session.execute(get_admin_id)
    admin_data = admin__data.scalars().one_or_none()
    if not admin_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sorry, this error from database. Try again later",
        )
    try:
        if message is not None:
            inserting_query = insert(SupportForUser).values(
                message=message, sender_id=user_id, receiver_id=admin_data.id
            )
            await session.execute(inserting_query)
        elif voice is not None:
            if (
                not voice.filename.endswith(".ogg")
                or not voice.filename.endswith(".wav")
                or not voice.filename.endswith(".mp3")
            ):
                raise HTTPException(
                    detail="You can send voice that given formats",
                    status_code=status.HTTP_406_NOT_ACCEPTABLE,
                )
            base_filename, file_extension = os.path.splitext(voice.filename)
            out_file = f"uploads/SupportVoiceMessages/{voice.filename}"
            index = 1
            while os.path.exists(out_file):
                out_file = f"uploads/SupportVoiceMessages/{base_filename}_{index}{file_extension}"
                index += 1
            async with aiofiles.open(out_file, "wb") as f:
                content = await voice.read()
                await f.write(content)
            voice_create = insert(SupportForUser).values(
                voice=str(out_file), sender_id=user_id, receiver_id=admin_data.id
            )
            await session.execute(voice_create)
        await session.commit()
        inserted_message = (
            select(SupportForUser)
            .where(SupportForUser.sender_id == user_id)
            .where(SupportForUser.receiver_id == admin_data.id)
            .order_by(SupportForUser.sent_at.desc())
        )
        inserted_message_data = await session.execute(inserted_message)
        inserted_message_result = inserted_message_data.scalars().first()
        user_data = select(Users).where(Users.id == inserted_message_result.sender_id)
        receiver_data = select(Users).where(
            Users.id == inserted_message_result.receiver_id
        )
        user__data = await session.execute(user_data)
        receiver__data = await session.execute(receiver_data)
        user_data = user__data.scalars().one()
        receiver_data = receiver__data.scalars().one()
        task_data = select(Tasks).where(Tasks.id == inserted_message_result.task_id)
        task__data = await session.execute(task_data)
        task = task__data.scalars().one()
        user_dict = {
            key: getattr(user_data, key)
            for key in user_data.__dict__.keys()
            if key != "password"
        }
        receiver_dict = {
            key: getattr(receiver_data, key)
            for key in receiver_data.__dict__.keys()
            if key != "password"
        }

        inserted_message_result.sender_id = user_dict
        inserted_message_result.receiver_id = receiver_dict
        inserted_message_result.task_id = task.__dict__

        return inserted_message_result
    except Exception as e:
        raise HTTPException(
            detail=str(e), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
