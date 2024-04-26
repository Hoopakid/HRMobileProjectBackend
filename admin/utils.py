from sqlalchemy import select

from models.models import Users


async def is_admin(user_id, session):
    user_query = select(Users).where((Users.id == user_id) & (Users.status is True))
    user__data = await session.execute(user_query)
    user = user__data.scalars()
    return user is not None
