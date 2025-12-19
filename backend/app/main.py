# backend/app/main.py

import os

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.routing import WebSocketRoute

# Διαφημίσεις
from app.services.advertisement_service import AdvertisementService
from app.models.advertisement import Advertisement

# Layout γηπέδου (ζώνες + screens + index)
from app.services.layout_service import LayoutService, get_screen_index
from app.models.layout_models import Zone, Screen, MultiIndexKey, ScreenRecommendation

# WebSockets (router + manager)
from app.websockets.websockets import router as websocket_router, ws_manager

# Placements
from app.models.placement_models import AdPlacement
from app.services.placement_service import PlacementService

app = FastAPI(title="Geo-Ads Backend")


@app.api_route("/health", methods=["GET", "HEAD"])
def health():
    return {"status": "ok"}



@app.get("/debug/ws_routes")
def debug_ws_routes():
    return [
        {"path": r.path, "name": getattr(r, "name", None), "type": r.__class__.__name__}
        for r in app.router.routes
        if isinstance(r, WebSocketRoute)
    ]


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(os.path.dirname(BASE_DIR), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# CORS (αργότερα θα σφιχτεί)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register WS routes
app.include_router(websocket_router)


@app.get("/")
def root():
    return {"message": "Geo-Ads backend is running"}


# -----------------------------
#  ΔΙΑΦΗΜΙΣΕΙΣ (HTTP API)
# -----------------------------
@app.get("/advertisements", response_model=list[Advertisement])
def list_advertisements():
    return AdvertisementService.get_all()


@app.get("/advertisements/zone/{zone_id}", response_model=list[Advertisement])
def list_advertisements_by_zone(zone_id: str):
    return AdvertisementService.get_by_zone(zone_id)


# -----------------------------
#  LAYOUT ΓΗΠΕΔΟΥ
# -----------------------------
@app.get("/layout", response_model=list[Zone])
def get_layout():
    return LayoutService.get_layout()


@app.get("/layout/zones/{zone_id}/screens", response_model=list[Screen])
def get_screens_by_zone(zone_id: str):
    index = get_screen_index()
    return index.query_by_zone(zone_id)


@app.get("/layout/zones/{zone_id}/screens/{row}/{col}", response_model=Screen)
def get_screen_by_grid(zone_id: str, row: int, col: int):
    index = get_screen_index()
    screen = index.query_by_grid(zone_id, row, col)
    if not screen:
        raise HTTPException(status_code=404, detail="Screen not found")
    return screen


@app.get("/layout/query/near", response_model=list[Screen])
def query_screens_near(
    x: float = Query(..., description="Grid X (col)"),
    y: float = Query(..., description="Grid Y (row)"),
    radius: float = Query(1.5, description="Μέγιστη απόσταση στο grid"),
    zone_id: str | None = Query(None, description="Φίλτρο ζώνης"),
):
    index = get_screen_index()
    return index.query_near(x, y, radius, zone_id)


@app.get("/layout/multiindex", response_model=list[MultiIndexKey])
def get_multiindex_keys(
    ad_category: str | None = Query(None, description="Κατηγορία διαφήμισης"),
    time_window: str | None = Query(None, description="Χρονικό παράθυρο"),
):
    index = get_screen_index()
    return index.build_keys(ad_category=ad_category, time_window=time_window)


@app.get("/layout/recommendation/screen", response_model=ScreenRecommendation)
def recommend_screen_endpoint(
    x: float = Query(...),
    y: float = Query(...),
    radius: float = Query(10.0),
    zone_id: str | None = Query(None),
    screen_type: str | None = Query(None),
    ad_category: str | None = Query(None),
    time_window: str | None = Query(None),
):
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


@app.get("/recommendation/advertisements/{ad_id}/screen", response_model=ScreenRecommendation)
def recommend_screen_for_ad(
    ad_id: int,
    x: float = Query(...),
    y: float = Query(...),
    radius: float = Query(10.0),
    screen_type: str | None = Query(None),
    ad_category: str | None = Query(None),
    time_window: str | None = Query(None),
):
    ad = AdvertisementService.get_by_id(ad_id)
    if ad is None:
        raise HTTPException(status_code=404, detail="Advertisement not found")

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
#  PLACEMENTS
# -----------------------------
@app.get("/placements", response_model=list[AdPlacement])
def list_placements():
    return PlacementService.list_all()


@app.get("/placements/screen/{screen_id}", response_model=list[AdPlacement])
def list_placements_by_screen(screen_id: str):
    return PlacementService.list_by_screen(screen_id)


@app.post("/placements/recommend_and_assign/advertisements/{ad_id}", response_model=AdPlacement)
async def recommend_and_assign_ad_for_screen(
    ad_id: int,
    x: float = Query(...),
    y: float = Query(...),
    radius: float = Query(10.0),
    screen_type: str | None = Query(None),
    ad_category: str | None = Query(None),
    time_window: str | None = Query(None),
):
    ad = AdvertisementService.get_by_id(ad_id)
    if ad is None:
        raise HTTPException(status_code=404, detail="Advertisement not found")

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

    key, _distance = result

    placement = PlacementService.assign_ad(ad_id=ad.id, key=key)

    # WS broadcast σε όλους τους connected /ws/placements clients
    await ws_manager.broadcast_placement_assigned(placement)

    return placement
