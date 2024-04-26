from models.models import Tasks
from fastapi_filter.contrib.sqlalchemy import Filter
from typing import Optional


class AdminFilter(Filter):
    degree: Optional[int] = None
    status: Optional[str] = None
    importance: Optional[str] = None

    class Constants:
        model = Tasks
        ordering_field_name = ("degree", "status", "importance")
        search_field_name = ("degree", "status", "importance")
