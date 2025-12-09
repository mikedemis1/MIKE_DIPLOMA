from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.advertisement_service import AdvertisementService
from app.services.layout_service import get_screen_index
from app.models.layout_models import MultiIndexKey, ScreenRecommendation
import asyncio

router = APIRouter()

# 👇 ΝΕΑ συνάρτηση για να διαβάζουμε διαφημίσεις από το service
async def fetch_ads():
    ads = AdvertisementService.get_all()
    # τα γυρνάμε σαν απλό JSON-serializable object
    return [ad.dict() for ad in ads]

# Σύνδεση WebSocket για διαφημίσεις
@router.websocket("/ws/ads")
async def websocket_ads(websocket: WebSocket):
    """
    Απλό WebSocket:
    - Ο client συνδέεται στο ws://127.0.0.1:8000/ws/ads
    - Κάθε 5 δευτερόλεπτα στέλνουμε τη λίστα με τις διαφημίσεις
    """
    await websocket.accept()
    print(" WebSocket client connected")

    try:
        while True:
            # Λαμβάνουμε τη λίστα με τις διαφημίσεις
            ads = await fetch_ads()  # Κάλεσε το υπάρχον HTTP endpoint /advertisements
            await websocket.send_json({
                "type": "ads_list",  # Είδος μηνύματος
                "data": ads  # Δεδομένα διαφημίσεων
            })
            await asyncio.sleep(5)  # Κάθε 5 δευτερόλεπτα

    except WebSocketDisconnect:
        print(" WebSocket client disconnected")

# Νέος WebSocket για Recommendation
@router.websocket("/ws/recommendation")
async def websocket_recommendation(websocket: WebSocket):
    """
    WebSocket για real-time recommendations.
    - Ο client στέλνει τις συντεταγμένες και την κατηγορία διαφήμισης
    - Ο server επιστρέφει την προτεινόμενη οθόνη.
    """
    await websocket.accept()
    print(" WebSocket client connected for recommendations")

    try:
        while True:
            data = await websocket.receive_json()

            ad_id = data.get("ad_id")
            x = data.get("x")
            y = data.get("y")
            radius = data.get("radius", 10.0)
            screen_type = data.get("screen_type", None)
            ad_category = data.get("ad_category", None)
            time_window = data.get("time_window", None)

            # Βρες τη διαφήμιση από το ad_id
            ad = AdvertisementService.get_by_id(ad_id)
            if not ad:
                await websocket.send_json({"error": "Advertisement not found"})
                continue

            # Βρες τη ζώνη από την διαφήμιση
            zone_id = ad.zone

            # Καλούμε το recommendation για την οθόνη
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
                await websocket.send_json({"error": "No suitable screen found"})
                continue

            # Παίρνουμε το κλειδί και την απόσταση
            key, distance = result

            # Στέλνουμε το αποτέλεσμα του recommendation στον client
            recommendation = ScreenRecommendation(
                screen_id=key.screen_id,
                zone_id=key.zone_id,
                x=key.x,
                y=key.y,
                screen_type=key.screen_type,
                ad_category=key.ad_category,
                time_window=key.time_window,
                distance=distance,
            )

            await websocket.send_json({
                "type": "screen_recommendation",
                "data": recommendation.dict()  # Επιστρέφουμε τα δεδομένα της προτεινόμενης οθόνης
            })

            await asyncio.sleep(5)  # Κάθε 5 δευτερόλεπτα

    except WebSocketDisconnect:
        print(" WebSocket client disconnected")
