from starlette import status

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException
from sqlalchemy import select, update, delete
from models.models import Users, Tasks
from auth.utils import verify_token
from database import get_async_session

mobile_router = APIRouter()


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
