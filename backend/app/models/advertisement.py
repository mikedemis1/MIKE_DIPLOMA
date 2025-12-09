# backend/app/models/advertisement.py
from pydantic import BaseModel


class Advertisement(BaseModel):
    """
    Μοντέλο διαφήμισης όπως είναι στη βάση:
    id, name, image_url, zone.
    """

    id: int
    name: str
    image_url: str | None = None
    zone: str
