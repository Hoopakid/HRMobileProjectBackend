import asyncio
import os
import datetime

from datetime import date
from typing import Optional

import aiofiles
import starlette.status as status
from fastapi_filter import FilterDepends

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, UploadFile

from database import get_async_session
from sqlalchemy.exc import NoResultFound
from sqlalchemy import select, insert, update, delete
from fastapi.exceptions import HTTPException
from fastapi.responses import FileResponse

from auth.schemas import UserLogin
from auth.auth import pwd_context
from auth.utils import generate_token, verify_token
from models.models import Users, TaskStatus, Tasks, Degree, AdditionForTasks
from .filters import AdminFilter
from .utils import is_admin
from .scheme import InsertTask, Task, DegreeScheme, EditDegreeScheme

admin_router = APIRouter()


@admin_router.post("/login")
async def login_user(
    user: UserLogin, session: AsyncSession = Depends(get_async_session)
):
    user_existing_query = select(Users).where(Users.email == user.email)
    user_existing = await session.execute(user_existing_query)
    user_data = user_existing.scalars().one()
    if pwd_context.verify(user.password, user_data.password):
        if user_data.status:
            token = generate_token(user_data.id)
            return token
        raise HTTPException(
            detail="This user does not have access to the admin panel",
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
        )
    else:
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number or password incorrect !!!",
        )


@admin_router.post("/create-task")
async def create_task(
    task: Task,
    token: dict = Depends(verify_token),
    session: AsyncSession = Depends(get_async_session),
):
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Token not provided"
        )
    user_id = token.get("user_id")
    if await is_admin(user_id, session) is False:
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail="This user does not have access to the admin panel",
        )
    if not isinstance(task.deadline, datetime.date):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Deadline must be a date",
        )
    user_existing = select(Users).where(Users.id == task.user)
    user__data = await session.execute(user_existing)
    if user__data.scalars().one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found that given id",
        )
    try:
        if task.deadline <= datetime.date.today():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Deadline cannot be in the past",
            )
        get_degree_query = select(Users).where(Users.id == user_id)
        degree__data = await session.execute(get_degree_query)
        degree_data = degree__data.scalars().one()
        task_in_db = InsertTask(
            **dict(task),
            degree=int(degree_data.degree),
            status=TaskStatus.not_completed.value,
        )
        query = insert(Tasks).values(**dict(task_in_db))
        await session.execute(query)
        await session.commit()
        task_info = InsertTask(**dict(task_in_db))
        return dict(task_info)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@admin_router.get("/get-task-by-id")
async def get_task_by_id(
    task_id: int,
    token: dict = Depends(verify_token),
    session: AsyncSession = Depends(get_async_session),
):
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Token not provided"
        )
    try:
        task_query = select(Tasks).where(Tasks.id == task_id)
        task__data = await session.execute(task_query)
        data = task__data.scalars().one()
        get_user = select(Users).where(Users.id == data.user)
        user__data = await session.execute(get_user)
        user_data = user__data.scalars().one()
        user_dict = {
            key: getattr(user_data, key)
            for key in user_data.__dict__.keys()
            if key != "password"
        }
        data.user = user_dict
        return data
    except NoResultFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@admin_router.get("/get-all-tasks")
async def get_all_tasks(
    token: dict = Depends(verify_token),
    session: AsyncSession = Depends(get_async_session),
):
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Token not provided"
        )
    try:
        tasks_query = select(Tasks)
        tasks_data = await session.execute(tasks_query)
        tasks = tasks_data.scalars().all()

        users_query = select(Users)
        users_data = await session.execute(users_query)
        users_dict = {user.id: user for user in users_data.scalars().all()}
        for task in tasks:
            user_id = task.user
            if user_id in users_dict:
                user_data = users_dict[user_id]
                user_dict = {
                    key: getattr(user_data, key)
                    for key in user_data.__dict__.keys()
                    if key != "password"
                }
                task.user = user_dict
            else:
                task.user = None

        return tasks
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@admin_router.patch("/update-task")
async def update_task(
    task_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    deadline: Optional[date] = None,
    importance: Optional[str] = None,
    user: Optional[int] = None,
    token: dict = Depends(verify_token),
    session: AsyncSession = Depends(get_async_session),
):
    if token is None:
        raise HTTPException(
            detail="Token not provided", status_code=status.HTTP_403_FORBIDDEN
        )
    user_id = token.get("user_id")
    if not await is_admin(user_id, session):
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail="This user does not have access to admin panel",
        )

    try:
        select_query = update(Tasks).where(Tasks.id == task_id)

        values_to_update = {}
        if title is not None:
            values_to_update["title"] = title
        if description is not None:
            values_to_update["description"] = description
        if deadline is not None:
            if not isinstance(deadline, datetime.date):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Deadline must be a date",
                )
            if deadline <= datetime.date.today():
                raise HTTPException(
                    status_code=status.HTTP_406_NOT_ACCEPTABLE,
                    detail="Deadline cannot be in the past",
                )
            values_to_update["deadline"] = deadline
        if importance is not None:
            values_to_update["importance"] = importance
        if user is not None:
            user_query = select(Users).where(Users.id == user)
            user__data = await session.execute(user_query)
            user_data = user__data.scalars().one()
            if not user_data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found",
                )
            values_to_update["user"] = user
            values_to_update["degree"] = user_data.degree
        update_query = select_query.values(values_to_update)
        await session.execute(update_query)
        await session.commit()

        info_query = select(Tasks).where(Tasks.id == task_id)
        info__data = await session.execute(info_query)
        info_data = info__data.scalars().one()
        get_user = select(Users).where(Users.id == info_data.user)
        user__data = await session.execute(get_user)
        user_data = user__data.scalars().one()
        user_dict = {
            key: getattr(user_data, key)
            for key in user_data.__dict__.keys()
            if key != "password"
        }
        info_data.user = user_dict

        return info_data
    except NoResultFound:
        raise HTTPException(
            detail="Task or user not found that given id",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@admin_router.delete("/delete-task")
async def destroy_task(
    task_id: int,
    token: dict = Depends(verify_token),
    session: AsyncSession = Depends(get_async_session),
):
    if token is None:
        raise HTTPException(
            detail="Token not provided", status_code=status.HTTP_403_FORBIDDEN
        )
    user_id = token.get("user_id")
    if not await is_admin(user_id, session):
        raise HTTPException(
            detail="This user does not have access to admin panel",
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
        )
    data = select(Tasks).where(Tasks.id == task_id)
    delete_data = await session.execute(data)
    if not delete_data.scalars().one_or_none():
        raise HTTPException(
            detail="Task not found that given id",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    try:
        delete_query = delete(Tasks).where(Tasks.id == task_id)
        await session.execute(delete_query)
        await session.commit()
        await session.close()
        return {"success": True, "status": status.HTTP_204_NO_CONTENT}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@admin_router.get("/get-tasks-by-filter")
async def get_tasks_by_filter(
    admin_filter: AdminFilter = FilterDepends(AdminFilter),
    token: dict = Depends(verify_token),
    session: AsyncSession = Depends(get_async_session),
):
    if token is None:
        raise HTTPException(
            detail="Token not provided", status_code=status.HTTP_403_FORBIDDEN
        )
    user_id = token.get("user_id")
    if not await is_admin(user_id, session):
        raise HTTPException(
            detail="This user does not have access to admin panel",
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
        )
    try:
        query = admin_filter.filter(select(Tasks))
        query__data = await session.execute(query)
        query_data = query__data.scalars().all()
        return query_data
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@admin_router.post("/create-degree")
async def create_degree(
    degree: DegreeScheme,
    token: dict = Depends(verify_token),
    session: AsyncSession = Depends(get_async_session),
):
    if token is None:
        raise HTTPException(
            detail="Token not provided", status_code=status.HTTP_403_FORBIDDEN
        )
    user_id = token.get("user_id")
    if not await is_admin(user_id, session):
        raise HTTPException(
            detail="This user does not have access to admin panel",
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
        )
    try:
        create_query = insert(Degree).values(degree=degree.degree)
        await session.execute(create_query)
        await session.commit()
        added_degree = select(Degree).filter_by(degree=degree.degree)
        added_degree_data = await session.execute(added_degree)
        added_degree_dict = added_degree_data.scalars().first()
        await session.close()
        return {
            "status": status.HTTP_201_CREATED,
            "success": True,
            "data": added_degree_dict,
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@admin_router.patch("/edit-degree")
async def edit_degree(
    degree: EditDegreeScheme,
    token: dict = Depends(verify_token),
    session: AsyncSession = Depends(get_async_session),
):
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Token not provided"
        )
    user_id = token.get("user_id")
    if not await is_admin(user_id, session):
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail="This user does not have access to admin panel",
        )
    degree_existing_query = select(Degree).where(Degree.id == degree.id)
    data = await session.execute(degree_existing_query)
    if not data.scalars().one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Degree not found that given id",
        )
    try:
        update_query = update(Degree).where(Degree.id == degree.id)
        values_to_update = {}
        if degree.new_degree is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New degree must be provided",
            )
        values_to_update["degree"] = degree.new_degree
        update_query = update_query.values(values_to_update)
        await session.execute(update_query)
        await session.commit()
        updated_degree = await session.execute(select(Degree).filter_by(id=degree.id))
        updated_degree_dict = updated_degree.scalars().first()

        await session.close()
        return {
            "success": True,
            "status": status.HTTP_200_OK,
            "degree": updated_degree_dict,
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@admin_router.get("/get-all-degrees")
async def get_all_degrees(
    token: dict = Depends(verify_token),
    session: AsyncSession = Depends(get_async_session),
):
    if not token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Token not provided"
        )
    user_id = token.get("user_id")
    if not await is_admin(user_id, session):
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail="This user does not have access to admin panel",
        )
    try:
        select_query = select(Degree)
        degrees__data = await session.execute(select_query)
        degrees_data = degrees__data.scalars().all()
        return degrees_data
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@admin_router.get("/degree-detail")
async def get_degree_detail(
    degree_id: int,
    token: dict = Depends(verify_token),
    session: AsyncSession = Depends(get_async_session),
):
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Token not provideds"
        )
    user_id = token.get("user_id")
    if not await is_admin(user_id, session):
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail="This user does not have access to admin panel",
        )
    degree_existing = select(Degree).where(Degree.id == degree_id)
    degree_data = await session.execute(degree_existing)
    if not degree_data.scalars().one_or_none():
        raise HTTPException(
            detail="Degree not found that given id",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    try:
        degree = select(Degree).where(Degree.id == degree_id)
        degree__data = await session.execute(degree)
        degree_data = degree__data.scalars().one()
        await session.commit()
        await session.close()
        return degree_data
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@admin_router.delete("/delete-degree")
async def delete_degree(
    degree_id: int,
    token: dict = Depends(verify_token),
    session: AsyncSession = Depends(get_async_session),
):
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Token not provided"
        )
    user_id = token.get("user_id")
    if not await is_admin(user_id, session):
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail="This user does not have access to admin panel",
        )
    degree_existing = select(Degree).where(Degree.id == degree_id)
    degree__data = await session.execute(degree_existing)
    if not degree__data.scalars().one_or_none():
        raise HTTPException(
            detail="Degree not found that given id",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    try:
        delete_query = delete(Degree).where(Degree.id == degree_id)
        await session.execute(delete_query)
        await session.commit()
        return {"success": True, "status": status.HTTP_204_NO_CONTENT}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@admin_router.post("/add-addition-to-task")
async def add_addition_to_task(
    task_id: int,
    file: UploadFile,
    token: dict = Depends(verify_token),
    session: AsyncSession = Depends(get_async_session),
):
    task_existing = select(Tasks).where(Tasks.id == task_id)
    task__data = await session.execute(task_existing)
    if not task__data.scalars().one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found that given id"
        )
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Token not provided"
        )
    user_id = token.get("user_id")
    if not await is_admin(user_id, session):
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail="This user does not have access to admin panel",
        )
    try:
        base_filename, file_extension = os.path.splitext(file.filename)
        out_file = f"uploads/AdditionForTasks/{file.filename}"
        index = 1
        while os.path.exists(out_file):
            out_file = (
                f"uploads/AdditionForTasks/{base_filename}_{index}{file_extension}"
            )
            index += 1

        async with aiofiles.open(out_file, "wb") as f:
            content = await file.read()
            await f.write(content)

        inserting_query = insert(AdditionForTasks).values(
            task_id=task_id, file=out_file
        )
        await session.execute(inserting_query)
        await session.commit()
        return FileResponse(out_file, filename=os.path.basename(out_file))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@admin_router.delete("/delete-addition-from-task")
async def delete_addition_from_task(
    addition_id: int,
    token: dict = Depends(verify_token),
    session: AsyncSession = Depends(get_async_session),
):
    if token is None:
        raise HTTPException(
            detail="Token not provided", status_code=status.HTTP_403_FORBIDDEN
        )
    user_id = token.get("user_id")
    if not await is_admin(user_id, session):
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail="This user does not have access to admin panel",
        )
    addition_existing = select(AdditionForTasks).where(
        AdditionForTasks.id == addition_id
    )
    addition__data = await session.execute(addition_existing)
    addition_data = addition__data.scalars().one_or_none()
    if not addition_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Addition not found that given id",
        )
    try:
        out_file = addition_data.file
        if os.path.exists(out_file):
            os.remove(out_file)
        delete_query = delete(AdditionForTasks).where(
            AdditionForTasks.id == addition_id
        )
        await session.execute(delete_query)
        await session.commit()
        await session.close()
        return {"success": True, "status": status.HTTP_204_NO_CONTENT}
    except Exception as e:
        raise HTTPException(detail=str(e), status_code=status.HTTP_400_BAD_REQUEST)


@admin_router.get("/get-all-additions")
async def get_all_additions(
    token: dict = Depends(verify_token),
    session: AsyncSession = Depends(get_async_session),
):
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Token not provided"
        )
    user_id = token.get("user_id")
    if not await is_admin(user_id, session):
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail="This user does not have access to the admin panel",
        )
    try:
        select_query = select(AdditionForTasks)
        additions_data = await session.execute(select_query)
        additions_data = additions_data.scalars().all()

        tasks_query = select(Tasks)
        tasks_data = await session.execute(tasks_query)
        tasks_dict = {task.id: task for task in tasks_data.scalars().all()}

        for addition in additions_data:
            task_id = addition.task_id
            if task_id in tasks_dict:
                addition.task_id = tasks_dict[task_id].__dict__
            else:
                addition.task_id = None

        return additions_data
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@admin_router.get("/get-addition-by-id")
async def get_addition_by_id(
    addition_id: int,
    token: dict = Depends(verify_token),
    session: AsyncSession = Depends(get_async_session),
):
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Token not provided"
        )

    user_id = token.get("user_id")
    if not await is_admin(user_id, session):
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail="This user does not have access to the admin panel",
        )

    try:
        addition_existing = select(AdditionForTasks).where(
            AdditionForTasks.id == addition_id
        )
        addition_data = await session.execute(addition_existing)
        addition_data = addition_data.scalars().one()
    except NoResultFound:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Addition not found with the given ID",
        )

    try:
        file_path = addition_data.file
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found, but addition exists",
            )
        return FileResponse(file_path, filename=os.path.basename(file_path))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@admin_router.get("/get-addition-by-path")
async def get_addition_by_path(
    path: str,
    token: dict = Depends(verify_token),
    session: AsyncSession = Depends(get_async_session),
):
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Token not provided"
        )
    user_id = token.get("user_id")
    if not await is_admin(user_id, session):
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail="This user does not have access to the admin panel",
        )
    try:
        addition_existing = select(AdditionForTasks).where(
            AdditionForTasks.file == path
        )
        addition_data = await session.execute(addition_existing)
        addition_data = addition_data.scalars().one()
    except NoResultFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Addition not found that given path",
        )
    try:
        path = addition_data.file
        if not os.path.exists(path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found, but addition exists",
            )
        return FileResponse(path, filename=os.path.basename(path))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@admin_router.patch("/update_addition")
async def update_addition(
    addition_id: int,
    new_file: UploadFile,
    token: dict = Depends(verify_token),
    session: AsyncSession = Depends(get_async_session),
):
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Token not provided"
        )
    user_id = token.get("user_id")
    if not await is_admin(user_id, session):
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail="This user does not have access to the admin panel",
        )
    try:
        existing_addition = select(AdditionForTasks).where(
            AdditionForTasks.id == addition_id
        )
        addition_data = await session.execute(existing_addition)
        addition_data = addition_data.scalars().one()
    except NoResultFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Addition not found with the given id",
        )
    try:
        base_filename, file_extension = os.path.splitext(new_file.filename)
        out_file = f"uploads/AdditionForTasks/{new_file.filename}"
        index = 1
        while os.path.exists(out_file):
            out_file = (
                f"uploads/AdditionForTasks/{base_filename}_{index}{file_extension}"
            )
            index += 1

        removable_path = addition_data.file
        if os.path.exists(removable_path):
            os.remove(removable_path)
        async with aiofiles.open(out_file, "wb") as f:
            content = await new_file.read()
            await f.write(content)
        update_query = (
            update(AdditionForTasks)
            .where(AdditionForTasks.id == addition_id)
            .values(file=out_file)
        )
        await session.execute(update_query)
        await session.commit()
        return {"message": "Addition updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
