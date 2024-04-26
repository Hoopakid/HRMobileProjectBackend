import os
from typing import List

import aiofiles
import redis

import starlette.status as status
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from passlib.context import CryptContext
from pydantic import EmailStr
from sqlalchemy import select, insert, update
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_async_session
from models.models import Users, Degree
from .schemas import UserInfo, InsertUser, UserLogin
from .utils import (
    send_mail,
    generate_token,
    verify_token,
    send_mail_for_forget_password,
    get_user_data,
)

redis_client = redis.StrictRedis(
    host="localhost", port=6379, db=0, decode_responses=True
)

auth_router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@auth_router.post("/register")
async def register_user(
    degree_id: int,
    first_name: str,
    last_name: str,
    phone_number: str,
    password: str,
    email: EmailStr,
    session: AsyncSession = Depends(get_async_session),
    user_photo: UploadFile = None,
):
    try:
        degree_existing_query = select(Degree).where(Degree.id == degree_id)
        degree__data = await session.execute(degree_existing_query)
        degree_data = degree__data.scalars().one_or_none()
        if not degree_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Degree not found that given id",
            )
        phone_number_existing_query = select(Users).where(
            Users.phone_number == phone_number
        )
        phone_number_existing = await session.execute(phone_number_existing_query)
        if phone_number_existing.scalars().one_or_none():
            return HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already exists !!!",
            )
        email_existing_query = select(Users).where(Users.email == email)
        email_existing = await session.execute(email_existing_query)
        if email_existing.scalars().one_or_none():
            return HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exists !!!",
            )
        not_hashed_password = password
        password = pwd_context.hash(password)
        out_file = ""
        if user_photo is not None:
            out_file = f"userPhotos/{user_photo.filename}"
            async with aiofiles.open(f"uploads/{out_file}", "wb") as f:
                content = await user_photo.read()
                await f.write(content)

        user_data = {
            "first_name": first_name,
            "last_name": last_name,
            "phone_number": phone_number,
            "email": email,
            "password": password,
            "degree": degree_id,
            "user_photo": out_file,
        }

        user_in_db = InsertUser(**user_data)
        insert_query = insert(Users).values(**dict(user_in_db)).returning(Users.id)
        insert__data = await session.execute(insert_query)
        await session.commit()
        user_id = insert__data.scalars().one()
        stts = True

        info_user = UserInfo(
            id=user_id,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
            degree=degree_id,
            email=email,
            user_photo=out_file,
            status=stts,
        )
        send_mail(email, not_hashed_password)
        return dict(info_user)

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@auth_router.post("/login")
async def login_user(
    user: UserLogin, session: AsyncSession = Depends(get_async_session)
):
    try:
        user_existing_query = select(Users).where(Users.email == user.email)
        user_existing = await session.execute(user_existing_query)
        user_data = user_existing.scalars().one()
        if pwd_context.verify(user.password, user_data.password):
            token = generate_token(user_data.id)
            return token
        else:
            return HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number or password incorrect !!!",
            )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# this api also used for admin panel
@auth_router.get("/user/user-info", response_model=UserInfo)
async def user_info(
    token: dict = Depends(verify_token),
    session: AsyncSession = Depends(get_async_session),
):
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Token not provided"
        )

    user_id = token.get("user_id")
    try:
        query = select(Users).where(Users.id == user_id)
        query_data = await session.execute(query)
        data = query_data.scalars().one()
        return UserInfo(
            **{
                key: (
                    getattr(data, key)
                    if getattr(data, key) is not None
                    else ("None" if isinstance(key, str) else 0)
                )
                for key in UserInfo.__fields__.keys()
            }
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@auth_router.get("/user/all-user-info", response_model=List[UserInfo])
async def user_info(
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
        query_data = await session.execute(query)
        data = query_data.scalars().all()

        user_info_list = []
        for user in data:
            user_info_list.append(
                UserInfo(
                    **{
                        key: (
                            getattr(user, key)
                            if getattr(user, key) is not None
                            else ("None" if isinstance(key, str) else 0)
                        )
                        for key in UserInfo.__fields__.keys()
                    }
                )
            )

        return user_info_list
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# this api also used for admin panel
@auth_router.patch("/user/edit-account", response_model=UserInfo)
async def edit_account(
    first_name: str = None,
    last_name: str = None,
    phone_number: str = None,
    email: EmailStr = None,
    token: dict = Depends(verify_token),
    session: AsyncSession = Depends(get_async_session),
):
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Token not provided"
        )

    user_id = token.get("user_id")
    try:
        update_query = update(Users).where(Users.id == user_id)

        values_to_update = {}
        if first_name is not None:
            values_to_update["first_name"] = first_name
        if last_name is not None:
            values_to_update["last_name"] = last_name
        if email is not None:
            email_existing_query = select(Users).where(Users.email == email)
            email_existing = await session.execute(email_existing_query)
            if email_existing.scalar():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already exists !!! Try again.",
                )
            values_to_update["email"] = email
        if phone_number is not None:
            phone_number_existing_query = select(Users).where(
                Users.phone_number == phone_number
            )
            phone_number_existing = await session.execute(phone_number_existing_query)
            if phone_number_existing.scalar():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Phone number already exists !!! Try again.",
                )
            values_to_update["phone_number"] = phone_number
        update_query = update_query.values(values_to_update)

        await session.execute(update_query)
        await session.commit()

        query = select(Users).where(Users.id == user_id)
        query_data = await session.execute(query)
        data = query_data.scalars().one()

        return UserInfo(
            **{
                key: (
                    getattr(data, key)
                    if getattr(data, key) is not None
                    else ("None" if isinstance(key, str) else 0)
                )
                for key in UserInfo.__fields__.keys()
            }
        )

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# this api also used for admin panel
@auth_router.get("/user/send-verification-change-password")
async def send_verification_to_change_password(
    token: dict = Depends(verify_token),
    session: AsyncSession = Depends(get_async_session),
):
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token not provided",
        )
    user_id = token.get("user_id")
    try:
        query = select(Users).where(Users.id == user_id)
        query_data = await session.execute(query)
        data = query_data.scalars().one()
        variable = send_mail_for_forget_password(data.email, data.first_name)
        redis_client.set(data.email, variable)
        return {"status": "success", "detail": "Check your email"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# this api also used for admin panel
@auth_router.patch("/user/change-password", response_model=UserInfo)
async def change_password(
    confirmation_code: int,
    new_password: str,
    new_password_confirmation: str,
    token: dict = Depends(verify_token),
    session: AsyncSession = Depends(get_async_session),
):
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token not provided",
        )
    user_id = token.get("user_id")
    user_data = await get_user_data(session, user_id)
    variable = redis_client.get(user_data.email)
    if variable is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please use this api again /auth/user/send-verification-change-password",
        )
    if int(confirmation_code) != int(variable):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation code is incorrect",
        )
    if new_password != new_password_confirmation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match",
        )
    user_id = token.get("user_id")

    try:
        password = pwd_context.hash(new_password)
        user_update_query = (
            update(Users).where(Users.id == user_id).values(password=password)
        )
        await session.execute(user_update_query)
        await session.commit()
        get_user = await get_user_data(session, user_id)
        redis_client.delete(user_data.email)
        return UserInfo(
            **{
                key: (
                    getattr(get_user, key)
                    if getattr(get_user, key) is not None
                    else ("None" if isinstance(key, str) else 0)
                )
                for key in UserInfo.__fields__.keys()
            }
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# this api also used for admin panel
@auth_router.patch("/user/update-photo", response_model=UserInfo)
async def update_user_photo(
    user_photo: UploadFile = File(...),
    token: dict = Depends(verify_token),
    session: AsyncSession = Depends(get_async_session),
):
    user_id = token.get("user_id")
    try:
        user_data = await get_user_data(session, user_id)
        if user_data is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        if user_data.user_photo:
            old_photo_path = f"uploads/{user_data.user_photo}"
            if os.path.exists(old_photo_path):
                os.remove(old_photo_path)

        new_photo_path = f"userPhotos/{user_photo.filename}"
        async with aiofiles.open(f"uploads/{new_photo_path}", "wb") as f:
            content = await user_photo.read()
            await f.write(content)

        user_data.user_photo = new_photo_path
        await session.commit()

        return UserInfo(
            **{
                key: (
                    getattr(user_data, key)
                    if getattr(user_data, key) is not None
                    else ("None" if isinstance(key, str) else 0)
                )
                for key in UserInfo.__fields__.keys()
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
