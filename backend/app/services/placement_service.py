# backend/app/services/placement_service.py

from datetime import datetime
from typing import List

from app.models.placement_models import AdPlacement
from app.models.layout_models import MultiIndexKey


class PlacementService:
    """
    Απλός in-memory πίνακας αναθέσεων.
    Δεν ακουμπάει βάση – όλα ζουν στη RAM του backend.
    """

    _placements: List[AdPlacement] = []

    @classmethod
    def assign_ad(cls, ad_id: int, key: MultiIndexKey) -> AdPlacement:
        """
        Δημιουργεί μια νέα ανάθεση διαφήμισης σε οθόνη,
        την αποθηκεύει στη λίστα και την επιστρέφει.
        """
        placement = AdPlacement(
            ad_id=ad_id,
            screen_id=key.screen_id,
            zone_id=key.zone_id,
            x=key.x,
            y=key.y,
            screen_type=key.screen_type,
            ad_category=key.ad_category,
            time_window=key.time_window,
            assigned_at=datetime.utcnow(),
        )
        cls._placements.append(placement)
        return placement

    @classmethod
    def list_all(cls) -> List[AdPlacement]:
        """Επιστρέφει όλες τις αναθέσεις."""
        return list(cls._placements)

    @classmethod
    def list_by_screen(cls, screen_id: str) -> List[AdPlacement]:
        """Επιστρέφει όλες τις αναθέσεις για συγκεκριμένη οθόνη."""
        return [p for p in cls._placements if p.screen_id == screen_id]
