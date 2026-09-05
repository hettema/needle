"""A project: a path to a repository that keeps plans the way the board reads them."""

from datetime import datetime

from pydantic import BaseModel

from domain.entrance import Entrance


class Project(BaseModel):
    slug: str
    name: str
    path: str
    registered_at: datetime
    entrance: Entrance | None = None
    """What a session started here reads as its constitution, as the board last
    read it at the door. None until a registration or a re-read has run since
    the reading existed."""
