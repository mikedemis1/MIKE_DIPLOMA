from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Διαφημίσεις
from app.services.advertisement_service import AdvertisementService
from app.models.advertisement import Advertisement

# Layout γηπέδου (ζώνες + screens + index)
from app.services.layout_service import LayoutService, get_screen_index
from app.models.layout_models import Zone, Screen, MultiIndexKey, ScreenRecommendation

# WebSocket router για real-time ads
from app.websockets.websockets import router as websocket_router

# Placements
from app.models.placement_models import AdPlacement
from app.services.placement_service import PlacementService


# Δημιουργία του FastAPI app
app = FastAPI(title="Geo-Ads Backend")


# backend/app/main.py
from starlette.routing import WebSocketRoute

@app.get("/debug/ws_routes")
def debug_ws_routes():
    return [
        {"path": r.path, "name": getattr(r, "name", None), "type": r.__class__.__name__}
        for r in app.router.routes
        if isinstance(r, WebSocketRoute)
    ]


import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(os.path.dirname(BASE_DIR), "static")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# CORS για να μιλάει άνετα το React (localhost:3000/3001/3002 κλπ)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # για δοκιμές τώρα, μετά το σφίγγουμε
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register WebSocket routes
app.include_router(websocket_router)


# -----------------------------
#  HEALTH CHECK
# -----------------------------
@app.get("/")
def root():
    return {"message": "Geo-Ads backend is running"}


# -----------------------------
#  ΔΙΑΦΗΜΙΣΕΙΣ (HTTP API)
# -----------------------------
@app.get("/advertisements", response_model=list[Advertisement])
def list_advertisements():
    """
    Επιστρέφει ΟΛΕΣ τις διαφημίσεις από τον πίνακα advertisements.
    """
    return AdvertisementService.get_all()


@app.get(
    "/advertisements/zone/{zone_id}",
    response_model=list[Advertisement],
)
def list_advertisements_by_zone(zone_id: str):
    """
    Επιστρέφει όλες τις διαφημίσεις για μια συγκεκριμένη ζώνη.
    Παράδειγμα:
      - /advertisements/zone/glassfloor
      - /advertisements/zone/megatron
    """
    return AdvertisementService.get_by_zone(zone_id)


# -----------------------------
#  LAYOUT ΓΗΠΕΔΟΥ (ΖΩΝΕΣ + SCREENS)
# -----------------------------
@app.get("/layout", response_model=list[Zone])
def get_layout():
    """
    Επιστρέφει όλο το layout:
    - GlassFloor (4x4)
    - Surrounding Screens (2x4)
    - Megatron Screens (2x2)
    """
    return LayoutService.get_layout()


@app.get("/layout/zones/{zone_id}/screens", response_model=list[Screen])
def get_screens_by_zone(zone_id: str):
    """
    Επιστρέφει όλα τα screens για μια συγκεκριμένη ζώνη.
    Π.χ. /layout/zones/glassfloor/screens
    """
    index = get_screen_index()
    return index.query_by_zone(zone_id)


@app.get(
    "/layout/zones/{zone_id}/screens/{row}/{col}",
    response_model=Screen,
)
def get_screen_by_grid(zone_id: str, row: int, col: int):
    """
    Επιστρέφει μία οθόνη (screen) με βάση:
      - zone_id (π.χ. 'glassfloor')
      - row, col (θέση στο grid)
    """
    index = get_screen_index()
    screen = index.query_by_grid(zone_id, row, col)
    if not screen:
        raise HTTPException(status_code=404, detail="Screen not found")
    return screen


@app.get(
    "/layout/query/near",
    response_model=list[Screen],
)
def query_screens_near(
    x: float = Query(..., description="Grid X (col)"),
    y: float = Query(..., description="Grid Y (row)"),
    radius: float = Query(1.5, description="Μέγιστη απόσταση στο grid"),
    zone_id: str | None = Query(
        None,
        description="Προαιρετικά: φίλτρο σε συγκεκριμένη ζώνη (π.χ. 'glassfloor')",
    ),
):
    """
    Σύνθετο query πάνω στον MultiDimScreenIndex.

    Παραδείγματα:
    - /layout/query/near?x=1.5&y=1.5&radius=2
    - /layout/query/near?x=1.5&y=1.5&radius=2&zone_id=glassfloor
    """
    index = get_screen_index()
    return index.query_near(x, y, radius, zone_id)


@app.get(
    "/layout/multiindex",
    response_model=list[MultiIndexKey],
)
def get_multiindex_keys(
    ad_category: str | None = Query(
        None,
        description="Προαιρετικά: κατηγορία διαφήμισης (π.χ. 'tech')",
    ),
    time_window: str | None = Query(
        None,
        description="Προαιρετικά: χρονικό παράθυρο (π.χ. 'prime_time')",
    ),
):
    """
    Demo endpoint για το Distributed Multi-Index Engine.

    Επιστρέφει για ΚΑΘΕ οθόνη ένα MultiIndexKey που συνδυάζει:
    - zone_id
    - (x, y) στο grid
    - screen_type
    - ad_category (αν δοθεί)
    - time_window (αν δοθεί)
    """
    index = get_screen_index()
    return index.build_keys(
        ad_category=ad_category,
        time_window=time_window,
    )


@app.get(
    "/layout/recommendation/screen",
    response_model=ScreenRecommendation,
)
def recommend_screen_endpoint(
    x: float = Query(..., description="Target X στο grid (col)"),
    y: float = Query(..., description="Target Y στο grid (row)"),
    radius: float = Query(10.0, description="Μέγιστη απόσταση αναζήτησης στο grid"),
    zone_id: str | None = Query(
        None, description="Προαιρετικό φίλτρο ζώνης (π.χ. 'glassfloor')"
    ),
    screen_type: str | None = Query(
        None, description="Προαιρετικό φίλτρο τύπου οθόνης (π.χ. 'glassfloor_tile')"
    ),
    ad_category: str | None = Query(
        None, description="Προαιρετικά: κατηγορία διαφήμισης (π.χ. 'tech')"
    ),
    time_window: str | None = Query(
        None, description="Προαιρετικά: χρονικό παράθυρο (π.χ. 'prime_time')"
    ),
):
    """
    Επιστρέφει την "προτεινόμενη" οθόνη για εμφάνιση μιας διαφήμισης
    γύρω από το σημείο (x, y) στο grid.

    Χρησιμοποιεί τον MultiDimScreenIndex.recommend_screen().
    """
    index = get_screen_index()
    result = index.recommend_screen(
        x=x,
        y=y,
        radius=radius,
        zone_id=zone_id,
        screen_type=screen_type,
        ad_category=ad_category,
        time_window=time_window,
    )

    if result is None:
        raise HTTPException(status_code=404, detail="No suitable screen found")

    key, distance = result

    return ScreenRecommendation(
        screen_id=key.screen_id,
        zone_id=key.zone_id,
        x=key.x,
        y=key.y,
        screen_type=key.screen_type,
        ad_category=key.ad_category,
        time_window=key.time_window,
        distance=distance,
    )


@app.get(
    "/recommendation/advertisements/{ad_id}/screen",
    response_model=ScreenRecommendation,
)
def recommend_screen_for_ad(
    ad_id: int,
    x: float = Query(..., description="Target X στο grid (col)"),
    y: float = Query(..., description="Target Y στο grid (row)"),
    radius: float = Query(10.0, description="Μέγιστη απόσταση αναζήτησης στο grid"),
    screen_type: str | None = Query(
        None, description="Προαιρετικό φίλτρο τύπου οθόνης (π.χ. 'glassfloor_tile')"
    ),
    ad_category: str | None = Query(
        None, description="Προαιρετικά: κατηγορία διαφήμισης (π.χ. 'tech')"
    ),
    time_window: str | None = Query(
        None, description="Προαιρετικά: χρονικό παράθυρο (π.χ. 'prime_time')"
    ),
):
    """
    Recommendation για ΣΥΓΚΕΚΡΙΜΕΝΗ διαφήμιση.

    1) Παίρνει τη διαφήμιση από τη βάση (AdvertisementService.get_by_id)
    2) Χρησιμοποιεί το zone της διαφήμισης σαν zone_id
    3) Καλεί MultiDimScreenIndex.recommend_screen(...)
    4) Επιστρέφει ScreenRecommendation
    """
    # 1) Βρες τη διαφήμιση
    ad = AdvertisementService.get_by_id(ad_id)
    if ad is None:
        raise HTTPException(status_code=404, detail="Advertisement not found")

    # 2) Recommendation μόνο μέσα στη ζώνη της διαφήμισης
    index = get_screen_index()
    result = index.recommend_screen(
        x=x,
        y=y,
        radius=radius,
        zone_id=ad.zone,
        screen_type=screen_type,
        ad_category=ad_category,
        time_window=time_window,
    )

    if result is None:
        raise HTTPException(status_code=404, detail="No suitable screen found")

    key, distance = result

    return ScreenRecommendation(
        screen_id=key.screen_id,
        zone_id=key.zone_id,
        x=key.x,
        y=key.y,
        screen_type=key.screen_type,
        ad_category=key.ad_category,
        time_window=key.time_window,
        distance=distance,
    )


# -----------------------------
#  PLACEMENTS (ΑΝΑΘΕΣΕΙΣ ΔΙΑΦΗΜΙΣΕΩΝ ΣΕ ΟΘΟΝΕΣ)
# -----------------------------
@app.get(
    "/placements",
    response_model=list[AdPlacement],
)
def list_placements():
    """
    Επιστρέφει όλες τις ενεργές αναθέσεις (in-memory).
    Χρήσιμο για debugging / dashboard του μηχανικού.
    """
    return PlacementService.list_all()


@app.get(
    "/placements/screen/{screen_id}",
    response_model=list[AdPlacement],
)
def list_placements_by_screen(screen_id: str):
    """
    Επιστρέφει όλες τις αναθέσεις για συγκεκριμένη οθόνη.
    Π.χ. /placements/screen/GF-1-1
    """
    return PlacementService.list_by_screen(screen_id)


@app.post(
    "/placements/recommend_and_assign/advertisements/{ad_id}",
    response_model=AdPlacement,
)
def recommend_and_assign_ad_for_screen(
    ad_id: int,
    x: float = Query(..., description="Target X στο grid (col)"),
    y: float = Query(..., description="Target Y στο grid (row)"),
    radius: float = Query(10.0, description="Μέγιστη απόσταση αναζήτησης στο grid"),
    screen_type: str | None = Query(
        None, description="Φίλτρο τύπου οθόνης (π.χ. 'glassfloor_tile')"
    ),
    ad_category: str | None = Query(
        None, description="Προαιρετικά: κατηγορία διαφήμισης (π.χ. 'tech')"
    ),
    time_window: str | None = Query(
        None, description="Προαιρετικά: χρονικό παράθυρο (π.χ. 'prime_time')"
    ),
):
    """
    Συνδυαστικό endpoint:

    1) Παίρνει τη διαφήμιση από τη βάση (ad_id)
    2) Χρησιμοποιεί το zone της διαφήμισης σαν default zone_id
    3) Καλεί το MultiDimScreenIndex.recommend_screen(...)
    4) Δημιουργεί ένα AdPlacement μέσω PlacementService.assign_ad(...)
    5) Επιστρέφει την ανάθεση
    """
    # 1) Βρες τη διαφήμιση
    ad = AdvertisementService.get_by_id(ad_id)
    if ad is None:
        raise HTTPException(status_code=404, detail="Advertisement not found")

    # 2) Recommendation μόνο μέσα στη ζώνη της διαφήμισης
    index = get_screen_index()
    result = index.recommend_screen(
        x=x,
        y=y,
        radius=radius,
        zone_id=ad.zone,  # ΠΕΡΙΟΡΙΣΜΟΣ: μόνο στη ζώνη της διαφήμισης
        screen_type=screen_type,
        ad_category=ad_category,
        time_window=time_window,
    )

    if result is None:
        raise HTTPException(status_code=404, detail="No suitable screen found")

    key, _distance = result  # εδώ δεν μας νοιάζει η απόσταση για την ανάθεση

    # 3) Δημιουργία placement
    placement = PlacementService.assign_ad(ad_id=ad.id, key=key)
    return placement
