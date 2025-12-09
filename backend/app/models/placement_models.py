# backend/app/models/placement_models.py

from datetime import datetime
from pydantic import BaseModel


class AdPlacement(BaseModel):
    """
    Μια ενεργή ανάθεση:
    - ποια διαφήμιση (ad_id)
    - σε ποια οθόνη (screen_id, zone_id)
    - με ποια χαρακτηριστικά του multi-index
    - πότε έγινε η ανάθεση (assigned_at)
    """

    ad_id: int
    screen_id: str
    zone_id: str

    x: float
    y: float

    screen_type: str | None = None
    ad_category: str | None = None
    time_window: str | None = None

    assigned_at: datetime
