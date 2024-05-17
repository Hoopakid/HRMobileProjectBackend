import enum

from sqlalchemy import (
    MetaData,
    Column,
    Integer,
    String,
    TIMESTAMP,
    Boolean,
    ForeignKey,
    Text,
    Date,
)
from sqlalchemy.orm import relationship

from database import Base
from datetime import datetime, date

metadata = MetaData()


class Degree(Base):
    __tablename__ = "degree"
    metadata = metadata
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    degree = Column(String, nullable=False)
    created = Column(TIMESTAMP, default=datetime.utcnow)


class Users(Base):
    __tablename__ = "users"
    metadata = metadata
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    first_name = Column(String)
    last_name = Column(String)
    phone_number = Column(String)
    email = Column(String)
    user_photo = Column(String, nullable=True)
    degree = Column(Integer, ForeignKey("degree.id"))
    password = Column(String)
    status = Column(Boolean, default=False)
    date_joined = Column(TIMESTAMP, default=datetime.utcnow)


class Room(Base):
    __tablename__ = "room"
    metadata = metadata
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    key = Column(String)
    sender_id = Column(Integer, ForeignKey("users.id"))
    receiver_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(TIMESTAMP, default=datetime.utcnow)


class Message(Base):
    __tablename__ = "messages"
    metadata = metadata
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    sender_id = Column(Integer, ForeignKey("users.id"))
    receiver_id = Column(Integer, ForeignKey("users.id"))
    message = Column(String)
    sent_at = Column(TIMESTAMP, default=datetime.utcnow)


# class Group(Base):
#     __tablename__ = "group"
#     metadata = metadata
#     id = Column(Integer, primary_key=True, index=True, autoincrement=True)
#     name = Column(String)
#     members = relationship("users", secondary="group_members", back_populates="group")
#     created_at = Column(TIMESTAMP, default=datetime.utcnow)
#
#
# class GroupMembers(Base):
#     __tablename__ = "group_members"
#     metadata = metadata
#     id = Column(Integer, primary_key=True, autoincrement=True)
#     user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
#     group_id = Column(Integer, ForeignKey("groups.id"), primary_key=True)
#     added_at = Column(TIMESTAMP, default=datetime.utcnow)


class TaskImportance(enum.Enum):
    high = "Yuqori"
    medium = "O'rta"
    low = "Past"


class TaskStatus(enum.Enum):
    completed = "Yakunlangan"
    not_completed = "Yakunlanmagan"


class Tasks(Base):
    __tablename__ = "tasks"
    metadata = metadata
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    degree = Column(Integer, ForeignKey("degree.id"))
    user = Column(Integer, ForeignKey("users.id"))
    created_at = Column(Date, default=date.today())
    deadline = Column(Date)
    importance = Column(String)
    status = Column(String, default=TaskStatus.not_completed.value)
    created_in_timestamp = Column(TIMESTAMP, default=datetime.utcnow)


class AdditionForTasks(Base):
    __tablename__ = "additions"
    metadata = metadata
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("tasks.id"))
    file = Column(String)
    added_at = Column(TIMESTAMP, default=datetime.utcnow)


# class QuestionsForTasks(Base):
#     __tablename__ = "questions"
#     metadata = metadata
#     id = Column(Integer, primary_key=True, index=True, autoincrement=True)
#     task_id = Column(Integer, ForeignKey("tasks.id"))
#     question = Column(String)
#
#
# class Choice(Base):
#     __tablename__ = "choices"
#     id = Column(Integer, primary_key=True, index=True, autoincrement=True)
#     question_id = Column(Integer, ForeignKey("questions.id"))
#     choice = Column(String)
#     correct = Column(Boolean, default=False)
#
#     question = relationship("questions", back_populates="choices")


class UserMessagesToAdminViaTask(Base):
    __tablename__ = "user_messages_to_admin_via_task"
    metadata = metadata
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    message = Column(String, nullable=True)
    voice = Column(String, nullable=True)
    sender_id = Column(Integer, ForeignKey("users.id"))
    task_id = Column(Integer, ForeignKey("tasks.id"))
    receiver_id = Column(Integer, ForeignKey("users.id"))
    sent_at = Column(TIMESTAMP, default=datetime.utcnow)


class SupportForUser(Base):
    __tablename__ = "support_for_user"
    metadata = metadata
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    message = Column(String, nullable=False)
    voice = Column(String, nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"))
    receiver_id = Column(Integer, ForeignKey("users.id"))
    sent_at = Column(TIMESTAMP, default=datetime.utcnow)
