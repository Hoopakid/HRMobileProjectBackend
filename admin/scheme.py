from typing import Optional
from sqlalchemy import Text
from models.models import TaskImportance, TaskStatus
from pydantic import BaseModel
from datetime import date


class InsertTask(BaseModel):
    title: str
    description: str
    degree: int
    user: int
    deadline: date
    importance: str
    status: Optional[str] = None


class Task(BaseModel):
    title: str
    description: str
    user: int
    deadline: date
    importance: str


class DegreeScheme(BaseModel):
    degree: str


class EditDegreeScheme(BaseModel):
    id: int
    new_degree: str
