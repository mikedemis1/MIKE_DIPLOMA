# backend/app/websockets/websockets.py

import asyncio
import json
import hashlib
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.advertisement_service import AdvertisementService

router = APIRouter()

def _hash_payload(obj) -> str:
    raw = json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

@router.websocket("/ws/ads")
async def websocket_ads(websocket: WebSocket):
    await websocket.accept()

    last_hash = None

    try:
        while True:
            ads = AdvertisementService().get_all()
            payload = {
                "type": "ads_list",
                "data": [ad.dict() for ad in ads],
            }

            h = _hash_payload(payload)
            if h != last_hash:
                await websocket.send_json(payload)
                last_hash = h

            await asyncio.sleep(2)  # polling interval
    except WebSocketDisconnect:
        return
