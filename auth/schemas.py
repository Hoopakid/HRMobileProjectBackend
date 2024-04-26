from fastapi import UploadFile, Depends
from pydantic import BaseModel, EmailStr, Field


class UserInfo(BaseModel):
    id: int
    first_name: str
    last_name: str
    phone_number: str
    degree: int = Depends(None)
    email: str
    user_photo: str = Depends(None)
    status: bool


class InsertUser(BaseModel):
    first_name: str
    last_name: str
    phone_number: str
    degree: int
    email: str
    password: str
    user_photo: str


class UserLogin(BaseModel):
    email: str
    password: str
