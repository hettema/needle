"""A project: a path to a repository that keeps plans the way the board reads them."""

from datetime import datetime

from pydantic import BaseModel


class Project(BaseModel):
    slug: str
    name: str
    path: str
    registered_at: datetime
