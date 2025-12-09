# backend/app/models/models.py
from pydantic import BaseModel
from typing import List

class Advertisement(BaseModel):
    id: int
    name: str
    image_url: str
    zone: str

class Zone(BaseModel):
    id: int
    name: str
    location: str
