# backend/app/models/layout_models.py

from typing import List, Optional, Dict, Any
from pydantic import BaseModel


class Screen(BaseModel):
    """
    Μοντέλο για μία οθόνη (screen) στο γήπεδο.
    """
    id: str
    zone_id: str
    row: int
    col: int

    # Τύπος οθόνης (π.χ. glassfloor_tile, surrounding_banner, megatron_panel)
    screen_type: str = "generic"

    # Προαιρετικά tags (π.χ. ["premium", "vip_side"])
    tags: List[str] = []

    # Ελεύθερο μεταδεδομένο για μελλοντική χρήση
    metadata: Dict[str, Any] = {}


class Zone(BaseModel):
    """
    Μοντέλο για ζώνη (GlassFloor, Surrounding, Megatron).
    """
    id: str
    name: str
    description: str
    rows: int
    cols: int
    screens: List[Screen]


class MultiIndexKey(BaseModel):
    """
    Πολυδιάστατο κλειδί για queries πάνω στις οθόνες.

    Συνδυάζει:
    - zone_id
    - 2D θέση (x, y) στο grid
    - τύπο οθόνης (screen_type)
    - κατηγορία διαφήμισης (ad_category)
    - χρονικό παράθυρο (time_window)
    """

    screen_id: str
    zone_id: str
    x: float
    y: float
    screen_type: str

    # Προαιρετικές "λογικές" διαστάσεις
    ad_category: Optional[str] = None     # π.χ. "tech", "sports"
    time_window: Optional[str] = None     # π.χ. "prime_time", "halftime"

    @classmethod
    def from_screen(
        cls,
        screen: Screen,
        ad_category: Optional[str] = None,
        time_window: Optional[str] = None,
    ) -> "MultiIndexKey":
        """
        Φτιάχνει ένα MultiIndexKey από ένα Screen + λογικές διαστάσεις.

        Προς το παρόν:
        - x = col
        - y = row
        """
        return cls(
            screen_id=screen.id,
            zone_id=screen.zone_id,
            x=float(screen.col),
            y=float(screen.row),
            screen_type=screen.screen_type,
            ad_category=ad_category,
            time_window=time_window,
        )


class ScreenRecommendation(BaseModel):
    """
    Απλό αποτέλεσμα recommendation:
    - ποια οθόνη επιλέχθηκε
    - με ποια χαρακτηριστικά
    - σε τι απόσταση από το target σημείο
    """
    screen_id: str
    zone_id: str
    x: float
    y: float
    screen_type: str
    ad_category: Optional[str] = None
    time_window: Optional[str] = None
    distance: float
