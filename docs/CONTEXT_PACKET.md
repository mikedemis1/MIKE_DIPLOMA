\# GEO-ADS — Context Packet (Canonical)



\## 1) Τι είναι

GEO-ADS: real-time σύστημα διαχείρισης και προβολής διαφημίσεων σε ζώνες (GlassFloor, Surrounding, Megatron).

Backend: FastAPI + PostgreSQL (ads) + in-memory placements + WebSockets.

Frontend: React UI.

Desktop: Electron app που ανοίγει το UI και σηκώνει backend τοπικά.



\## 2) Αρχιτεκτονική (high level)

\- Electron:

&nbsp; - φορτώνει React build (local file)

&nbsp; - ξεκινά backend process (uvicorn)

\- Backend:

&nbsp; - GET /advertisements (DB)

&nbsp; - GET /layout (in-memory)

&nbsp; - POST /placements/recommend\_and\_assign/advertisements/{ad\_id}?x=\&y=\&radius=

&nbsp; - WS /ws/ads (poll DB -> ads\_list only when changed via hash)

&nbsp; - WS /ws/placements (snapshot + placement\_assigned events)

\- DB:

&nbsp; - table advertisements(id, name, image\_url, zone)

&nbsp; - images served from /static/ads/\*



\## 3) Current status (τι δουλεύει τώρα)

\- Backend endpoints λειτουργούν όταν DB είναι up.

\- WS /ws/ads στέλνει ads\_list όταν αλλάξει payload.

\- WS /ws/placements κάνει broadcast placement\_assigned από HTTP assign.

\- Electron ανοίγει UI και σηκώνει backend.



\## 4) Known flaws (πρέπει να κλείσουν)

\- No auth/authz: HTTP/WS είναι public (οποιοσδήποτε μπορεί να συνδεθεί/κάνει assign).

\- /ws/placements snapshot πρέπει να είναι πραγματικό (PlacementService.list\_all), όχι placeholder.

\- /ws/ads κάνει polling DB ανά client (DoS/latency surface).

\- DB connections ανοίγουν/κλείνουν ανά request (χωρίς pooling).

\- Electron τρέχει backend με dev-style flags (π.χ. --reload) -> θέλει production-safe start.



\## 5) Acceptance criteria (τρέχον milestone)

1\) Electron: 1-click run, backend starts reliably without dev reload.

2\) /ws/placements: real snapshot + placement\_assigned on every assign.

3\) Frontend: placements είναι backend-authoritative (όχι local-only demo state).

4\) Security milestone: JWT auth + scopes for placements read/write + WS auth.



\## 6) How to run (Windows)

\- Backend (from /backend):

&nbsp; python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

\- DB:

&nbsp; docker compose up -d

\- WS test:

&nbsp; wscat -c ws://127.0.0.1:8000/ws/placements

&nbsp; wscat -c ws://127.0.0.1:8000/ws/ads



\## 7) Key files (μην στέλνονται όλα στο chat)

Backend:

\- backend/app/main.py

\- backend/app/websockets/websockets.py

\- backend/app/services/placement\_service.py

\- backend/app/services/advertisement\_service.py

\- backend/app/config.py

Desktop:

\- desktop/geo-ads-desktop/main.js

\- desktop/geo-ads-desktop/package.json

Frontend:

\- frontend/geo-ads-frontend/src/VisualBoard.js

\- frontend/geo-ads-frontend/src/App.js



\## 8) Chat protocol (κανόνας)

Σε νέο chat στέλνω:

\- docs/CONTEXT\_PACKET.md

\- docs/CONTRACTS.md

\- και μόνο τα 1–3 αρχεία που αλλάζουμε στη φάση + τα test outputs.



