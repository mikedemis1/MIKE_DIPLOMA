# backend/app/services/layout_service.py

from math import hypot
from app.models.layout_models import Zone, Screen, MultiIndexKey


class LayoutService:
    """
    Κεντρική υπηρεσία που ξέρει τη διάταξη των οθονών στο γήπεδο.
    Προς το παρόν είναι static (in-memory), χωρίς βάση.
    """

    @staticmethod
    def get_layout() -> list[Zone]:
        zones: list[Zone] = []

        # 1️⃣ GlassFloor: 4x4
        gf_screens: list[Screen] = []
        for row in range(4):
            for col in range(4):
                gf_screens.append(
                    Screen(
                        id=f"GF-{row}-{col}",
                        zone_id="glassfloor",
                        row=row,
                        col=col,
                        screen_type="glassfloor_tile",  # ΝΕΟ
                    )
                )

        zones.append(
            Zone(
                id="glassfloor",
                name="GlassFloor",
                description="Γυάλινο γήπεδο στο κέντρο",
                rows=4,
                cols=4,
                screens=gf_screens,
            )
        )

        # 2️⃣ Surrounding: 2x4
        sur_screens: list[Screen] = []
        for row in range(2):
            for col in range(4):
                sur_screens.append(
                    Screen(
                        id=f"SUR-{row}-{col}",
                        zone_id="surrounding",
                        row=row,
                        col=col,
                        screen_type="surrounding_banner",  # ΝΕΟ
                    )
                )

        zones.append(
            Zone(
                id="surrounding",
                name="Surrounding Screens",
                description="Περιμετρικές οθόνες γύρω από το γήπεδο",
                rows=2,
                cols=4,
                screens=sur_screens,
            )
        )

        # 3️⃣ Megatron: 2x2
        mega_screens: list[Screen] = []
        for row in range(2):
            for col in range(2):
                mega_screens.append(
                    Screen(
                        id=f"MEGA-{row}-{col}",
                        zone_id="megatron",
                        row=row,
                        col=col,
                        screen_type="megatron_panel",  # ΝΕΟ
                    )
                )

        zones.append(
            Zone(
                id="megatron",
                name="Megatron Screens",
                description="Κεντρικές μεγάλες οθόνες (Megatron)",
                rows=2,
                cols=2,
                screens=mega_screens,
            )
        )

        return zones


# ------------------------------------------
#  ΠΟΛΥΔΙΑΣΤΑΤΟΣ INDEX (ένα μόνο αντίγραφο!)
# ------------------------------------------


class MultiDimScreenIndex:
    """
    Πιο έξυπνος index για screens.

    Κρατάει:
    - ανά ζώνη (zone_id)
    - ανά grid (zone_id, row, col)
    - 2D συντεταγμένες (x, y) για κοντινά queries

    Για αρχή όλα είναι in-memory (single process),
    ώστε αργότερα να το "σπάσουμε" σε distributed nodes.
    """

    def __init__(self, zones: list[Zone]):
        # 1) Αποθηκεύουμε τις ζώνες
        self._zones_by_id: dict[str, Zone] = {z.id: z for z in zones}

        # 2) Flat λίστα με όλα τα screens
        self._screens: list[Screen] = [s for z in zones for s in z.screens]

        # 3) Index ανά ζώνη
        self._screens_by_zone: dict[str, list[Screen]] = {}

        # 4) Index ανά grid (zone_id, row, col)
        self._screens_by_grid: dict[tuple[str, int, int], Screen] = {}

        # 5) Index για 2D κοντινά queries (x, y, screen)
        #    Προς το παρόν linear scan. Αργότερα μπαίνει R-Tree.
        self._coords: list[tuple[float, float, Screen]] = []

        for screen in self._screens:
            # Ανά ζώνη
            self._screens_by_zone.setdefault(screen.zone_id, []).append(screen)

            # Ανά grid
            grid_key = (screen.zone_id, screen.row, screen.col)
            self._screens_by_grid[grid_key] = screen

            # 2D θέση στο "grid space"
            # Για αρχή: x = col, y = row (απλό μοντέλο)
            x = float(screen.col)
            y = float(screen.row)
            self._coords.append((x, y, screen))

    # -----------------------------
    #  ΑΠΛΑ QUERIES (όπως πριν)
    # -----------------------------

    def query_by_zone(self, zone_id: str) -> list[Screen]:
        """
        Επιστρέφει όλα τα screens για μια ζώνη.
        Πλήρως συμβατό με το παλιό NaiveScreenIndex.
        """
        return list(self._screens_by_zone.get(zone_id, []))

    def query_by_grid(self, zone_id: str, row: int, col: int) -> Screen | None:
        """
        Επιστρέφει ένα screen με βάση zone + row + col.
        """
        return self._screens_by_grid.get((zone_id, row, col))

    # -----------------------------
    #  ΠΟΛΥΔΙΑΣΤΑΤΑ QUERIES
    # -----------------------------

    def query_near(
        self,
        x: float,
        y: float,
        radius: float,
        zone_id: str | None = None,
    ) -> list[Screen]:
        """
        Σύνθετο query:
        - Δώσε μου όλα τα screens σε απόσταση <= radius
          από το σημείο (x, y) στο grid.
        - Προαιρετικά φιλτράρισμα σε συγκεκριμένη ζώνη.

        Προς το παρόν:
        - κάνει απλό O(n) έλεγχο με hypot
        - αργότερα μπορούμε να το αντικαταστήσουμε με R-Tree.
        """
        results: list[Screen] = []

        for sx, sy, screen in self._coords:
            if zone_id is not None and screen.zone_id != zone_id:
                continue

            if hypot(sx - x, sy - y) <= radius:
                results.append(screen)

        return results

    def get_all_screens(self) -> list[Screen]:
        """Χρήσιμο για debugging / testing."""
        return list(self._screens)

    def build_keys(
        self,
        ad_category: str | None = None,
        time_window: str | None = None,
    ) -> list[MultiIndexKey]:
        """
        Δημιουργεί μια λίστα από MultiIndexKey αντικείμενα
        για ΟΛΑ τα screens του γηπέδου.

        Προς το παρόν:
        - βάζουμε ίδια ad_category / time_window σε όλα,
          όπως τα δώσει το endpoint.
        """
        return [
            MultiIndexKey.from_screen(
                screen,
                ad_category=ad_category,
                time_window=time_window,
            )
            for screen in self._screens
        ]


    def recommend_screen(
        self,
        x: float,
        y: float,
        radius: float = 10.0,
        zone_id: str | None = None,
        screen_type: str | None = None,
        ad_category: str | None = None,
        time_window: str | None = None,
    ) -> tuple[MultiIndexKey, float] | None:
        """
        Βρίσκει την "καλύτερη" οθόνη για μια διαφήμιση γύρω από ένα σημείο (x, y).

        Βήματα:
        1) Παίρνουμε όλα τα κοντινά screens (query_near)
        2) Αν έχει δοθεί screen_type, φιλτράρουμε
        3) Επιλέγουμε αυτό με τη μικρότερη απόσταση
        4) Γυρνάμε (MultiIndexKey, distance)

        Προς το παρόν η "ποιότητα" = μικρότερη γεωμετρική απόσταση.
        Αργότερα μπορεί να προσθέσω scoring (π.χ. Megatron > GlassFloor).
        """
        # 1) Κοντινά υποψήφια
        candidates = self.query_near(x=x, y=y, radius=radius, zone_id=zone_id)

        # 2) Φίλτρο screen_type (αν ζητηθεί)
        if screen_type is not None:
            candidates = [s for s in candidates if s.screen_type == screen_type]

        if not candidates:
            return None

        # 3) Βρες το πιο κοντινό
        def distance_to_screen(s: Screen) -> float:
            return hypot(float(s.col) - x, float(s.row) - y)

        best_screen = min(candidates, key=distance_to_screen)
        best_distance = distance_to_screen(best_screen)

        # 4) Φτιάξε το κλειδί
        key = MultiIndexKey.from_screen(
            best_screen,
            ad_category=ad_category,
            time_window=time_window,
        )

        return key, best_distance


# SINGLETON (ένα index για όλο το backend)
_INDEX: MultiDimScreenIndex | None = None


def get_screen_index() -> MultiDimScreenIndex:
    """
    Lazy δημιουργία του index.
    Καλείται από τα endpoints του main.py.
    """
    global _INDEX
    if _INDEX is None:
        zones = LayoutService.get_layout()
        _INDEX = MultiDimScreenIndex(zones)
    return _INDEX
