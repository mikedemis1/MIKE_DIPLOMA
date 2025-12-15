# backend/app/websockets/websockets.py

import asyncio
import json
import hashlib
from typing import Optional, Set, Tuple

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder

from app.services.advertisement_service import AdvertisementService
from app.services.placement_service import PlacementService
from app.services.layout_service import get_screen_index

router = APIRouter()


def _hash_payload(obj) -> str:
    raw = json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class WSManager:
    def __init__(self) -> None:
        self.placements_clients: Set[WebSocket] = set()

    async def register_placements(self, ws: WebSocket) -> None:
        await ws.accept()
        self.placements_clients.add(ws)
        print(f"[WS] placements client connected ({len(self.placements_clients)})")

        # REAL snapshot από RAM
        snapshot = jsonable_encoder(PlacementService.list_all())
        await ws.send_json({"v": 1, "type": "placements_snapshot", "data": snapshot})

    def unregister_placements(self, ws: WebSocket) -> None:
        self.placements_clients.discard(ws)
        print(f"[WS] placements client disconnected ({len(self.placements_clients)})")

    async def broadcast_placement_assigned(self, placement) -> None:
        payload = {"v": 1, "type": "placement_assigned", "data": jsonable_encoder(placement)}
        dead = []
        for ws in list(self.placements_clients):
            try:
                await ws.send_json(payload)
            except Exception as e:
                print(f"[WS] send FAILED: {e}")
                dead.append(ws)

        for ws in dead:
            self.unregister_placements(ws)


ws_manager = WSManager()


@router.websocket("/ws/ads")
async def websocket_ads(ws: WebSocket):
    await ws.accept()
    last_hash = None
    try:
        while True:
            ads = AdvertisementService.get_all()
            payload = {"v": 1, "type": "ads_list", "data": [ad.dict() for ad in ads]}

            h = _hash_payload(payload)
            if h != last_hash:
                await ws.send_json(payload)
                last_hash = h

            await asyncio.sleep(2)
    except WebSocketDisconnect:
        return


@router.websocket("/ws/placements")
async def websocket_placements(ws: WebSocket):
    await ws_manager.register_placements(ws)
    try:
        # κρατάμε open + πιάνουμε disconnect σωστά
        while True:
            await ws.receive()
    except WebSocketDisconnect:
        ws_manager.unregister_placements(ws)


@router.websocket("/ws/recommendation")
async def websocket_recommendation(ws: WebSocket):
    await ws.accept()
    index = get_screen_index()

    try:
        while True:
            raw = await ws.receive_text()
            try:
                payload = json.loads(raw)
            except Exception:
                await ws.send_json({"error": "Invalid JSON"})
                continue

            ad_id = payload.get("ad_id")
            x = payload.get("x")
            y = payload.get("y")
            radius = payload.get("radius", 10.0)

            screen_type = payload.get("screen_type")
            ad_category = payload.get("ad_category")
            time_window = payload.get("time_window")

            if x is None or y is None:
                await ws.send_json({"error": "Missing x/y"})
                continue

            zone_id: Optional[str] = None
            if ad_id is not None:
                ad = AdvertisementService.get_by_id(int(ad_id))
                if ad is None:
                    await ws.send_json({"error": "Advertisement not found"})
                    continue
                zone_id = ad.zone

            result = index.recommend_screen(
                x=float(x),
                y=float(y),
                radius=float(radius),
                zone_id=zone_id,
                screen_type=screen_type,
                ad_category=ad_category,
                time_window=time_window,
            )

            if result is None:
                await ws.send_json({"error": "No suitable screen found"})
                continue

            key, distance = result

            await ws.send_json(
                {
                    "v": 1,
                    "type": "screen_recommendation",
                    "data": {
                        "screen_id": key.screen_id,
                        "zone_id": key.zone_id,
                        "x": key.x,
                        "y": key.y,
                        "screen_type": key.screen_type,
                        "ad_category": key.ad_category,
                        "time_window": key.time_window,
                        "distance": distance,
                    },
                }
            )

    except WebSocketDisconnect:
        return
