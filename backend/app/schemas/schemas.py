# backend/app/schemas/schemas.py
from pydantic import BaseModel
from .models import Advertisement, Zone

class AdvertisementSchema(BaseModel):
    name: str
    image_url: str
    zone: str

class ZoneSchema(BaseModel):
    name: str
    location: str
