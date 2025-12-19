// frontend/geo-ads-frontend/src/VisualBoard.js
import React, { useEffect, useState } from "react";
import "./App.css";

/** Βάση URL του backend (εκεί τρέχει ο FastAPI) */
const BACKEND_BASE_URL =
  process.env.REACT_APP_BACKEND_BASE_URL || "http://127.0.0.1:8000";
const WS_BASE_URL = BACKEND_BASE_URL.replace(/^http/, "ws");
/**
 * Τοπικός χάρτης: όνομα διαφήμισης -> URL εικόνας στο backend/static.
 * Χρησιμοποιούμε ΠΛΗΡΕΣ URL για να δουλεύει σωστά μέσα στο Electron.
 */
const AD_IMAGE_MAP = {
  "Apple iPhone 14 Promo": `${BACKEND_BASE_URL}/static/galaxy_s25_ultra.jpg`,
  "Samsung Galaxy S21": `${BACKEND_BASE_URL}/static/galaxy_s25_ultra.jpg`,
  "Sony TV Sale": `${BACKEND_BASE_URL}/static/sony_headphones.jpg`,
  "Coca Cola Banner": `${BACKEND_BASE_URL}/static/cocacola_lineup.jpg`,
  "Pepsi Banner": `${BACKEND_BASE_URL}/static/cocacola_lineup.jpg`,
  "Nike Air Max 2023": `${BACKEND_BASE_URL}/static/nike_airmax_red.jpg`,
};

/**
 * Επιλογή τελικού image URL για κάθε διαφήμιση.
 */
function resolveAdImageUrl(ad) {
  if (!ad) return null;

  // 1) Source of truth: DB image_url
  if (ad.image_url) {
    if (ad.image_url.startsWith("http://") || ad.image_url.startsWith("https://")) {
      return ad.image_url;
    }
    return `${BACKEND_BASE_URL}${ad.image_url}`;
  }

  // 2) Fallback: hardcoded map (μόνο αν λείπει image_url)
  if (AD_IMAGE_MAP[ad.name]) {
    return AD_IMAGE_MAP[ad.name];
  }

  return null;
}



/**
 * Υπολογίζει το CSS για κάθε tile του mosaic.
 */
function computeMosaicBackgroundStyle(config, screen) {
  if (!config || !screen) return {};

  const totalRows = config.maxRow - config.minRow + 1;
  const totalCols = config.maxCol - config.minCol + 1;

  const rowIndex = screen.row - config.minRow;
  const colIndex = screen.col - config.minCol;

  const rowPercent =
    totalRows === 1 ? 50 : (rowIndex / (totalRows - 1)) * 100;
  const colPercent =
    totalCols === 1 ? 50 : (colIndex / (totalCols - 1)) * 100;

  return {
    backgroundImage: `url(${config.imageUrl})`,
    backgroundSize: `${totalCols * 100}% ${totalRows * 100}%`,
    backgroundPosition: `${colPercent}% ${rowPercent}%`,
    backgroundRepeat: "no-repeat",
  };
}

function VisualBoard() {
  // -----------------------------
  //  Layout / ζώνες
  // -----------------------------
  const [zones, setZones] = useState([]);
  const [selectedZoneId, setSelectedZoneId] = useState(null);
  const [loadingLayout, setLoadingLayout] = useState(true);
  const [layoutError, setLayoutError] = useState(null);

  // -----------------------------
  //  Διαφημίσεις ανά ζώνη
  // -----------------------------
  const [zoneAds, setZoneAds] = useState([]);
  const [adsLoading, setAdsLoading] = useState(false);
  const [adsError, setAdsError] = useState(null);

  // -----------------------------
  //  WebSocket status (ads)
  // -----------------------------
  const [wsStatus, setWsStatus] = useState("disconnected");

  // -----------------------------
  //  Επιλογή οθονών & placements
  // -----------------------------
  const [selectionMode, setSelectionMode] = useState("single"); // "single" | "multi"
  const [selectedScreen, setSelectedScreen] = useState(null); // για single
  const [selectedScreens, setSelectedScreens] = useState([]); // για multi / mosaic
  const [placements, setPlacements] = useState({}); // placements[screenId] = ad

  // -----------------------------
  //  Mosaic state
  // -----------------------------
  const [mosaicMode, setMosaicMode] = useState(false);
  const [mosaicSelectedAdId, setMosaicSelectedAdId] = useState(null);
  const [mosaicConfigs, setMosaicConfigs] = useState({}); // zoneId -> config

  // -----------------------------
  //  HTTP Recommendation state
  // -----------------------------
  const [recX, setRecX] = useState(1);
  const [recY, setRecY] = useState(1);
  const [recRadius, setRecRadius] = useState(10);
  const [recScreenType, setRecScreenType] = useState("");
  const [recAdCategory, setRecAdCategory] = useState("");
  const [recTimeWindow, setRecTimeWindow] = useState("");
  const [recAdId, setRecAdId] = useState(null);

  const [recLoading, setRecLoading] = useState(false);
  const [recError, setRecError] = useState(null);
  const [recommendationInfo, setRecommendationInfo] = useState(null);
  const [recommendedScreenId, setRecommendedScreenId] = useState(null);

  // -----------------------------
  //  WebSocket Recommendation
  // -----------------------------
  const [wsRecEnabled, setWsRecEnabled] = useState(false);
  const [wsRecStatus, setWsRecStatus] = useState("disconnected");

  // -----------------------------
  //  Near query state (/layout/query/near)
  // -----------------------------
  const [nearX, setNearX] = useState(1);
  const [nearY, setNearY] = useState(1);
  const [nearRadius, setNearRadius] = useState(2);
  const [nearResults, setNearResults] = useState([]);
  const [nearLoading, setNearLoading] = useState(false);
  const [nearError, setNearError] = useState(null);

  // -----------------------------
  //  MultiIndex inspector state
  // -----------------------------
  const [miAdCategory, setMiAdCategory] = useState("");
  const [miTimeWindow, setMiTimeWindow] = useState("");
  const [multiIndexKeys, setMultiIndexKeys] = useState([]);
  const [miLoading, setMiLoading] = useState(false);
  const [miError, setMiError] = useState(null);
  

  // =====================
  //  Φόρτωση LAYOUT
  // =====================
  useEffect(() => {
    async function fetchLayout() {
      try {
        setLoadingLayout(true);
        setLayoutError(null);

        const res = await fetch(`${BACKEND_BASE_URL}/layout`);
        if (!res.ok) {
          throw new Error("HTTP " + res.status);
        }
        const data = await res.json();
        setZones(data);

        if (data.length > 0) {
          setSelectedZoneId(data[0].id);
        }
      } catch (err) {
        console.error("Error fetching layout:", err);
        setLayoutError("Δεν μπορώ να φορτώσω το layout από το backend.");
      } finally {
        setLoadingLayout(false);
      }
    }

    fetchLayout();
  }, []);

  // =====================
  //  Φόρτωση ADS ανά ΖΩΝΗ
  // =====================
  useEffect(() => {
    if (!selectedZoneId) return;

    async function fetchZoneAds() {
      try {
        setAdsLoading(true);
        setAdsError(null);

        const res = await fetch(
          `${BACKEND_BASE_URL}/advertisements/zone/${selectedZoneId}`
        );
        if (!res.ok) {
          throw new Error("HTTP " + res.status);
        }
        const data = await res.json();
        setZoneAds(data);
      } catch (err) {
        console.error("Error fetching ads:", err);
        setAdsError("Δεν μπορώ να φορτώσω τις διαφημίσεις για αυτή τη ζώνη.");
        setZoneAds([]);
      } finally {
        setAdsLoading(false);
      }
    }

    fetchZoneAds();
  }, [selectedZoneId]);

  // =====================
  //  WebSocket για /ws/ads (status)
  // =====================
  useEffect(() => {
    const ws = new WebSocket(`${WS_BASE_URL}/ws/ads`);


    ws.onopen = () => {
      setWsStatus("connected");
    };

    ws.onclose = () => {
      setWsStatus("disconnected");
    };

    ws.onerror = () => {
      setWsStatus("error");
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        console.log("WS /ads message:", msg);
      } catch (e) {
        console.log("WS /ads raw:", event.data);
      }
    };

    return () => {
      ws.close();
    };
  }, []);

  // =====================
  //  WebSocket Recommendation (/ws/recommendation)
  // =====================
  useEffect(() => {
    if (!wsRecEnabled) {
      setWsRecStatus("disconnected");
      return;
    }

    const ws = new WebSocket(`${WS_BASE_URL}/ws/recommendation`);

    let timerId = null;

    ws.onopen = () => {
      setWsRecStatus("connected");

      // Στέλνουμε περιοδικά τις παραμέτρους
      timerId = setInterval(() => {
        const currentAdId =
          recAdId || (zoneAds.length > 0 ? zoneAds[0].id : null);

        if (!currentAdId) {
          setWsRecStatus("no-ad");
          return;
        }

        const payload = {
          ad_id: currentAdId,
          x: recX,
          y: recY,
          radius: recRadius,
          screen_type: recScreenType || null,
          ad_category: recAdCategory || null,
          time_window: recTimeWindow || null,
        };

        ws.send(JSON.stringify(payload));
      }, 3000);
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);

        if (msg.error) {
          setRecError(msg.error);
          return;
        }

        if (msg.type === "screen_recommendation" && msg.data) {
          const data = msg.data;
          setRecommendationInfo(data);
          setRecommendedScreenId(data.screen_id);
          setRecError(null);
        }
      } catch (err) {
        console.error("WS recommendation parse error:", err);
      }
    };

    ws.onerror = () => {
      setWsRecStatus("error");
    };

    ws.onclose = () => {
      setWsRecStatus("disconnected");
      if (timerId) clearInterval(timerId);
    };

    return () => {
      if (timerId) clearInterval(timerId);
      ws.close();
    };
    // Θέλουμε να ξαναστήνεται όταν αλλάζει η σημαία ή οι βασικές παράμετροι
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [wsRecEnabled, recX, recY, recRadius, recScreenType, recAdCategory, recTimeWindow, recAdId, zoneAds]);

  // =====================
  //  Βοηθητικά για επιλογές
  // =====================
  function isScreenSelected(screen) {
    if (!screen) return false;

    if (mosaicMode) {
      return selectedScreens.includes(screen.id);
    }

    if (selectionMode === "single") {
      return selectedScreen && selectedScreen.id === screen.id;
    }
    return selectedScreens.includes(screen.id);
  }

  // default ad αν δεν έχει ορίσει κάτι ο τεχνικός
  function getAdForScreen(index, screen) {
    if (placements[screen.id]) {
      return placements[screen.id];
    }
    if (!zoneAds || zoneAds.length === 0) return null;
    const adIndex = index % zoneAds.length;
    return zoneAds[adIndex];
  }

  function handleScreenClick(screen) {
    if (!screen) return;

    if (mosaicMode) {
      setSelectedScreens((prev) => {
        if (prev.includes(screen.id)) {
          return prev.filter((id) => id !== screen.id);
        }
        return [...prev, screen.id];
      });
      return;
    }

    if (selectionMode === "single") {
      setSelectedScreen(screen);
      return;
    }

    setSelectedScreens((prev) => {
      if (prev.includes(screen.id)) {
        return prev.filter((id) => id !== screen.id);
      }
      return [...prev, screen.id];
    });
  }

  function handleAdChoice(ad) {
    if (!ad) return;

    if (selectionMode === "single") {
      if (!selectedScreen) return;

      setPlacements((prev) => ({
        ...prev,
        [selectedScreen.id]: ad,
      }));
      setSelectedScreen(null);
      return;
    }

    if (selectedScreens.length === 0) return;

    setPlacements((prev) => {
      const next = { ...prev };
      selectedScreens.forEach((id) => {
        next[id] = ad;
      });
      return next;
    });
    setSelectedScreens([]);
  }

  function handleClearAd() {
    if (selectionMode === "single") {
      if (!selectedScreen) return;
      setPlacements((prev) => {
        const copy = { ...prev };
        delete copy[selectedScreen.id];
        return copy;
      });
      setSelectedScreen(null);
      return;
    }

    if (selectedScreens.length === 0) return;

    setPlacements((prev) => {
      const copy = { ...prev };
      selectedScreens.forEach((id) => {
        delete copy[id];
      });
      return copy;
    });
    setSelectedScreens([]);
  }

  // =====================
  //  Mosaic handlers
  // =====================
  function handleApplyMosaic() {
    const currentZone = zones.find((z) => z.id === selectedZoneId);
    if (!currentZone) return;

    if (!mosaicMode) {
      alert("Ενεργοποίησε πρώτα το Mosaic mode.");
      return;
    }

    if (!mosaicSelectedAdId) {
      alert("Επίλεξε πρώτα διαφήμιση για το mosaic.");
      return;
    }

    if (selectedScreens.length === 0) {
      alert("Επίλεξε πρώτα οθόνες για το mosaic.");
      return;
    }

    const screensInZone = currentZone.screens.filter((s) =>
      selectedScreens.includes(s.id)
    );
    if (screensInZone.length === 0) {
      alert("Δεν βρέθηκαν οθόνες για mosaic.");
      return;
    }

    const rows = screensInZone.map((s) => s.row);
    const cols = screensInZone.map((s) => s.col);
    const minRow = Math.min(...rows);
    const maxRow = Math.max(...rows);
    const minCol = Math.min(...cols);
    const maxCol = Math.max(...cols);

    const expectedCount = (maxRow - minRow + 1) * (maxCol - minCol + 1);
    if (expectedCount !== screensInZone.length) {
      alert(
        "Για Mosaic, οι οθόνες πρέπει να σχηματίζουν ένα συνεχόμενο ορθογώνιο (χωρίς κενά)."
      );
      return;
    }

    const ad = zoneAds.find((a) => a.id === mosaicSelectedAdId);
    if (!ad) {
      alert("Δεν βρέθηκε η διαφήμιση για mosaic.");
      return;
    }

    const imageUrl = resolveAdImageUrl(ad);
    if (!imageUrl) {
      alert("Η διαφήμιση δεν έχει διαθέσιμη εικόνα για mosaic.");
      return;
    }

    const config = {
      adId: ad.id,
      adName: ad.name,
      imageUrl,
      minRow,
      maxRow,
      minCol,
      maxCol,
    };

    setMosaicConfigs((prev) => ({
      ...prev,
      [currentZone.id]: config,
    }));

    setPlacements((prev) => {
      const copy = { ...prev };
      screensInZone.forEach((s) => {
        copy[s.id] = ad;
      });
      return copy;
    });

    setSelectedScreens([]);
  }

  function handleClearMosaic() {
    if (!selectedZoneId) return;
    setMosaicConfigs((prev) => {
      const copy = { ...prev };
      delete copy[selectedZoneId];
      return copy;
    });
  }

  // =====================
  //  HTTP Recommendation handlers
  // =====================

  function clearRecommendation() {
    setRecommendationInfo(null);
    setRecommendedScreenId(null);
    setRecError(null);
  }

  async function handleRecommendGeneric() {
    if (!selectedZoneId) return;
    setRecLoading(true);
    setRecError(null);
    try {
      const params = new URLSearchParams();
      params.append("x", String(recX));
      params.append("y", String(recY));
      params.append("radius", String(recRadius));
      params.append("zone_id", selectedZoneId);
      if (recScreenType.trim()) params.append("screen_type", recScreenType);
      if (recAdCategory.trim()) params.append("ad_category", recAdCategory);
      if (recTimeWindow.trim()) params.append("time_window", recTimeWindow);

      const res = await fetch(
        `${BACKEND_BASE_URL}/layout/recommendation/screen?${params.toString()}`
      );
      if (!res.ok) throw new Error("HTTP " + res.status);
      const data = await res.json();
      setRecommendationInfo(data);
      setRecommendedScreenId(data.screen_id);
    } catch (err) {
      console.error("Recommendation error (generic):", err);
      setRecError("Σφάλμα στο recommendation (γενικό).");
      clearRecommendation();
    } finally {
      setRecLoading(false);
    }
  }

  async function handleRecommendForAd() {
    if (!recAdId) {
      alert("Επίλεξε πρώτα διαφήμιση για recommendation.");
      return;
    }
    setRecLoading(true);
    setRecError(null);
    try {
      const params = new URLSearchParams();
      params.append("x", String(recX));
      params.append("y", String(recY));
      params.append("radius", String(recRadius));
      if (recScreenType.trim()) params.append("screen_type", recScreenType);
      if (recAdCategory.trim()) params.append("ad_category", recAdCategory);
      if (recTimeWindow.trim()) params.append("time_window", recTimeWindow);

      const res = await fetch(
        `${BACKEND_BASE_URL}/recommendation/advertisements/${recAdId}/screen?${params.toString()}`
      );
      if (!res.ok) throw new Error("HTTP " + res.status);
      const data = await res.json();
      setRecommendationInfo(data);
      setRecommendedScreenId(data.screen_id);
    } catch (err) {
      console.error("Recommendation error (ad):", err);
      setRecError("Σφάλμα στο recommendation για συγκεκριμένη διαφήμιση.");
      clearRecommendation();
    } finally {
      setRecLoading(false);
    }
  }

  // =====================
  //  Near query handlers (/layout/query/near)
  // =====================
  async function handleNearQuery() {
    if (!selectedZoneId) return;
    setNearLoading(true);
    setNearError(null);
    try {
      const params = new URLSearchParams();
      params.append("x", String(nearX));
      params.append("y", String(nearY));
      params.append("radius", String(nearRadius));
      params.append("zone_id", selectedZoneId);

      const res = await fetch(
        `${BACKEND_BASE_URL}/layout/query/near?${params.toString()}`
      );
      if (!res.ok) throw new Error("HTTP " + res.status);
      const data = await res.json();
      setNearResults(data);
    } catch (err) {
      console.error("Near query error:", err);
      setNearError("Σφάλμα στο near query.");
      setNearResults([]);
    } finally {
      setNearLoading(false);
    }
  }

  // =====================
  //  MultiIndex inspector handlers
  // =====================
  async function handleLoadMultiIndex() {
    setMiLoading(true);
    setMiError(null);
    try {
      const params = new URLSearchParams();
      if (miAdCategory.trim()) params.append("ad_category", miAdCategory);
      if (miTimeWindow.trim()) params.append("time_window", miTimeWindow);

      const res = await fetch(
        `${BACKEND_BASE_URL}/layout/multiindex?${params.toString()}`
      );
      if (!res.ok) throw new Error("HTTP " + res.status);
      const data = await res.json();
      setMultiIndexKeys(data);
    } catch (err) {
      console.error("MultiIndex error:", err);
      setMiError("Σφάλμα στο φόρτωμα MultiIndex keys.");
      setMultiIndexKeys([]);
    } finally {
      setMiLoading(false);
    }
  }

  const selectedZone =
    zones.find((z) => z.id === selectedZoneId) || null;
  const currentMosaicConfig = selectedZone
    ? mosaicConfigs[selectedZone.id] || null
    : null;

  const activeSelectionCount =
    selectionMode === "single"
      ? selectedScreen
        ? 1
        : 0
      : selectedScreens.length;

  const showAssignmentPanel = !mosaicMode && activeSelectionCount > 0;

  return (
    <div className="app-root">
      <header className="app-header">
        <h1>GEO-ADS Visual Board</h1>
        <p className="app-subtitle">
          Ζώνες οθονών – multi-zone layout με recommendation &amp; multi-index engine
        </p>
        <p className="ws-status">
          WebSocket /ws/ads: <strong>{wsStatus}</strong> | WS recommendation:{" "}
          <strong>{wsRecStatus}</strong>
        </p>
      </header>

      <main className="app-main">
        {/* SIDEBAR ΖΩΝΩΝ */}
        <aside className="zones-sidebar">
          <h2>Ζώνες</h2>

          {loadingLayout && <p>Φόρτωση layout...</p>}
          {layoutError && <p className="error-text">{layoutError}</p>}

          <ul className="zones-list">
            {zones.map((zone) => (
              <li key={zone.id}>
                <button
                  className={
                    "zone-button" +
                    (zone.id === selectedZoneId ? " zone-button-active" : "")
                  }
                  onClick={() => {
                    setSelectedZoneId(zone.id);
                    setSelectedScreen(null);
                    setSelectedScreens([]);
                    clearRecommendation();
                  }}
                >
                  {zone.name}
                </button>
              </li>
            ))}
          </ul>

          {/* MultiIndex inspector (αριστερά για "research" feeling) */}
          <div className="multiindex-panel">
            <h3>MultiIndex Inspector</h3>
            <div className="mi-inputs">
              <input
                type="text"
                placeholder="ad_category (π.χ. tech)"
                value={miAdCategory}
                onChange={(e) => setMiAdCategory(e.target.value)}
              />
              <input
                type="text"
                placeholder="time_window (π.χ. prime_time)"
                value={miTimeWindow}
                onChange={(e) => setMiTimeWindow(e.target.value)}
              />
              <button onClick={handleLoadMultiIndex} disabled={miLoading}>
                Φόρτωση κλειδιών
              </button>
            </div>
            {miError && <p className="error-text small-text">{miError}</p>}
            {miLoading && <p>Φόρτωση...</p>}
            {multiIndexKeys.length > 0 && (
              <p className="small-text">
                Keys: {multiIndexKeys.length} (δείξε τα 5 πρώτα στη διπλωματική
                ως παράδειγμα).
              </p>
            )}
          </div>
        </aside>

        {/* ΚΥΡΙΑ ΠΕΡΙΟΧΗ ΖΩΝΗΣ */}
        <section className="zone-preview">
          {selectedZone ? (
            <>
              <h2>{selectedZone.name}</h2>
              <p className="zone-description">
                {selectedZone.description} – Grid: {selectedZone.rows} x{" "}
                {selectedZone.cols}
              </p>

              {/* Επιλογή mode (single/multi) */}
              <div className="selection-mode">
                <span>Λειτουργία επιλογής: </span>
                <button
                  className={
                    "selection-mode-btn" +
                    (selectionMode === "single"
                      ? " selection-mode-btn-active"
                      : "")
                  }
                  onClick={() => {
                    setSelectionMode("single");
                    setSelectedScreens([]);
                  }}
                >
                  Μονή οθόνη
                </button>
                <button
                  className={
                    "selection-mode-btn" +
                    (selectionMode === "multi"
                      ? " selection-mode-btn-active"
                      : "")
                  }
                  onClick={() => {
                    setSelectionMode("multi");
                    setSelectedScreen(null);
                  }}
                >
                  Πολλαπλές (ίδια διαφήμιση)
                </button>
              </div>

              {/* MOSAIC CONTROLS */}
              <div className="mosaic-controls">
                <div className="mosaic-mode-buttons">
                  <button
                    className={
                      "mosaic-mode-btn" + (!mosaicMode ? " active" : "")
                    }
                    onClick={() => {
                      setMosaicMode(false);
                      setSelectedScreens([]);
                    }}
                  >
                    Απλό mode
                  </button>
                  <button
                    className={
                      "mosaic-mode-btn" + (mosaicMode ? " active" : "")
                    }
                    onClick={() => {
                      setMosaicMode(true);
                      setSelectionMode("multi");
                      setSelectedScreen(null);
                    }}
                  >
                    Mosaic mode
                  </button>
                </div>

                <div className="mosaic-ad-picker">
                  <div className="mosaic-label">Διαφήμιση για Mosaic:</div>
                  {zoneAds.length === 0 ? (
                    <span>Δεν υπάρχουν διαθέσιμες διαφημίσεις.</span>
                  ) : (
                    <div className="ad-picker-list">
                      {zoneAds.map((ad) => (
                        <button
                          key={ad.id}
                          className={
                            "ad-picker-btn" +
                            (mosaicSelectedAdId === ad.id
                              ? " ad-picker-btn-active"
                              : "")
                          }
                          onClick={() => setMosaicSelectedAdId(ad.id)}
                        >
                          {ad.name}
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                <div className="mosaic-actions">
                  <button
                    className="mosaic-apply-btn"
                    onClick={handleApplyMosaic}
                    disabled={
                      !mosaicMode ||
                      !mosaicSelectedAdId ||
                      selectedScreens.length === 0
                    }
                  >
                    Εφάρμοσε Mosaic στις επιλεγμένες οθόνες
                  </button>
                  <button
                    className="mosaic-clear-btn"
                    onClick={handleClearMosaic}
                    disabled={!currentMosaicConfig}
                  >
                    Καθάρισε Mosaic στη ζώνη
                  </button>
                  <span className="zone-layout-hint">
                    {mosaicMode
                      ? "Επίλεξε tiles που σχηματίζουν ορθογώνιο (π.χ. 4x4) και μετά πάτα 'Εφάρμοσε Mosaic'."
                      : "Για να κάνεις το γήπεδο μία ενιαία εικόνα, ενεργοποίησε το Mosaic mode."}
                  </span>
                </div>
              </div>

              {/* RECOMMENDATION PANEL */}
              <div className="recommendation-panel">
                <h3>Recommendation Engine</h3>
                <p className="small-text">
                  Συντεταγμένες στο grid (x=col, y=row). Δοκίμασε π.χ. (1.5, 1.5).
                </p>

                <div className="recommendation-grid">
                  <label>
                    X (col):
                    <input
                      type="number"
                      value={recX}
                      onChange={(e) => setRecX(parseFloat(e.target.value))}
                    />
                  </label>
                  <label>
                    Y (row):
                    <input
                      type="number"
                      value={recY}
                      onChange={(e) => setRecY(parseFloat(e.target.value))}
                    />
                  </label>
                  <label>
                    Radius:
                    <input
                      type="number"
                      value={recRadius}
                      onChange={(e) =>
                        setRecRadius(parseFloat(e.target.value))
                      }
                    />
                  </label>
                  <label>
                    Screen type:
                    <input
                      type="text"
                      value={recScreenType}
                      onChange={(e) => setRecScreenType(e.target.value)}
                      placeholder="π.χ. glassfloor_tile"
                    />
                  </label>
                  <label>
                    Ad category:
                    <input
                      type="text"
                      value={recAdCategory}
                      onChange={(e) => setRecAdCategory(e.target.value)}
                      placeholder="π.χ. tech"
                    />
                  </label>
                  <label>
                    Time window:
                    <input
                      type="text"
                      value={recTimeWindow}
                      onChange={(e) => setRecTimeWindow(e.target.value)}
                      placeholder="π.χ. prime_time"
                    />
                  </label>
                </div>

                <div className="recommendation-actions">
                  <button
                    onClick={handleRecommendGeneric}
                    disabled={recLoading}
                  >
                    Προτεινόμενη οθόνη (generic)
                  </button>

                  <div className="recommendation-ad-select">
                    <span>Διαφήμιση:</span>
                    <select
                      value={recAdId || ""}
                      onChange={(e) =>
                        setRecAdId(
                          e.target.value ? Number(e.target.value) : null
                        )
                      }
                    >
                      <option value="">-- καμία --</option>
                      {zoneAds.map((ad) => (
                        <option key={ad.id} value={ad.id}>
                          {ad.name}
                        </option>
                      ))}
                    </select>
                    <button
                      onClick={handleRecommendForAd}
                      disabled={recLoading || !recAdId}
                    >
                      Προτεινόμενη οθόνη για διαφήμιση
                    </button>
                  </div>

                  <div className="recommendation-ws-toggle">
                    <label>
                      <input
                        type="checkbox"
                        checked={wsRecEnabled}
                        onChange={(e) => setWsRecEnabled(e.target.checked)}
                      />
                      Real-time WebSocket recommendation
                    </label>
                  </div>

                  <button
                    onClick={clearRecommendation}
                    disabled={!recommendationInfo}
                  >
                    Καθαρισμός αποτελέσματος
                  </button>
                </div>

                {recLoading && <p>Υπολογισμός recommendation...</p>}
                {recError && <p className="error-text">{recError}</p>}
                {recommendationInfo && (
                  <div className="recommendation-result">
                    <p>
                      Προτεινόμενη οθόνη:{" "}
                      <strong>{recommendationInfo.screen_id}</strong> (zone:{" "}
                      {recommendationInfo.zone_id}, x:{recommendationInfo.x}, y:
                      {recommendationInfo.y})
                    </p>
                    <p>
                      Απόσταση στο grid:{" "}
                      {recommendationInfo.distance.toFixed(2)}
                    </p>
                  </div>
                )}
              </div>

              {/* NEAR QUERY PANEL */}
              <div className="near-panel">
                <h3>Near Query (/layout/query/near)</h3>
                <div className="near-grid">
                  <label>
                    X:
                    <input
                      type="number"
                      value={nearX}
                      onChange={(e) => setNearX(parseFloat(e.target.value))}
                    />
                  </label>
                  <label>
                    Y:
                    <input
                      type="number"
                      value={nearY}
                      onChange={(e) => setNearY(parseFloat(e.target.value))}
                    />
                  </label>
                  <label>
                    Radius:
                    <input
                      type="number"
                      value={nearRadius}
                      onChange={(e) =>
                        setNearRadius(parseFloat(e.target.value))
                      }
                    />
                  </label>
                  <button onClick={handleNearQuery} disabled={nearLoading}>
                    Εκτέλεση near query
                  </button>
                </div>
                {nearError && <p className="error-text">{nearError}</p>}
                {nearResults.length > 0 && (
                  <p className="small-text">
                    Βρέθηκαν {nearResults.length} κοντινές οθόνες (μπορείς να
                    τις περιγράψεις στη διπλωματική).
                  </p>
                )}
              </div>

              {/* INFO για ads */}
              <div className="ads-status">
                {adsLoading && <p>Φόρτωση διαφημίσεων...</p>}
                {adsError && <p className="error-text">{adsError}</p>}
                {!adsLoading && !adsError && zoneAds.length === 0 && (
                  <p className="warning-text">
                    Δεν υπάρχουν διαφημίσεις για αυτή τη ζώνη στη βάση
                    (πίνακας <code>advertisements</code>).
                  </p>
                )}
              </div>

              {/* GRID με screens + ads */}
              <div className="zone-layout">
                <p className="zone-layout-title">
                  Layout οθονών (κάθε πλακίδιο = μία Screen + διαφήμιση)
                </p>

                <div
                  className="stadium-layout-grid"
                  style={{
                    gridTemplateColumns: `repeat(${selectedZone.cols}, 1fr)`,
                  }}
                >
                  {selectedZone.screens.map((screen, index) => {
                    const ad = getAdForScreen(index, screen);
                    const selected = isScreenSelected(screen);

                    const imgSrc = resolveAdImageUrl(ad);
                    const isInMosaic =
                      !!currentMosaicConfig &&
                      screen.row >= currentMosaicConfig.minRow &&
                      screen.row <= currentMosaicConfig.maxRow &&
                      screen.col >= currentMosaicConfig.minCol &&
                      screen.col <= currentMosaicConfig.maxCol;

                    const isRecommended =
                      recommendedScreenId === screen.id;

                    return (
                      <div
                        key={screen.id}
                        className={
                          "screen-tile zone-" +
                          selectedZone.id +
                          (selected ? " screen-tile-selected" : "") +
                          (isInMosaic ? " screen-tile-mosaic" : "") +
                          (isRecommended ? " screen-tile-recommended" : "")
                        }
                        onClick={() => handleScreenClick(screen)}
                      >
                        {ad ? (
                          <>
                            {isInMosaic ? (
                              <div
                                className="mosaic-img-wrapper"
                                style={computeMosaicBackgroundStyle(
                                  currentMosaicConfig,
                                  screen
                                )}
                              />
                            ) : (
                              imgSrc && (
                                <img
                                  src={imgSrc}
                                  alt={ad.name}
                                  className="screen-img"
                                />
                              )
                            )}
                            <div className="screen-meta">
                              <div className="screen-ad-name">{ad.name}</div>
                              <div className="screen-pos">
                                ({screen.row},{screen.col})
                              </div>
                            </div>
                          </>
                        ) : (
                          <>
                            <div className="screen-id">{screen.id}</div>
                            <div className="screen-pos">
                              ({screen.row},{screen.col})
                            </div>
                          </>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* PANEL επιλογής διαφήμισης (ΜΟΝΟ εκτός Mosaic mode) */}
              {showAssignmentPanel && (
                <div className="ad-picker">
                  <h3>
                    Επιλογή διαφήμισης για{" "}
                    {selectionMode === "single"
                      ? `οθόνη ${
                          selectedScreen ? selectedScreen.id : ""
                        }`
                      : `${activeSelectionCount} οθόνες`}
                  </h3>

                  {zoneAds.length === 0 ? (
                    <p>Δεν υπάρχουν διαθέσιμες διαφημίσεις για αυτή τη ζώνη.</p>
                  ) : (
                    <div className="ad-picker-grid">
                      {zoneAds.map((ad) => {
                        const imgSrc = resolveAdImageUrl(ad);
                        return (
                          <button
                            key={ad.id}
                            className="ad-picker-item"
                            onClick={() => handleAdChoice(ad)}
                          >
                            {imgSrc && (
                              <img
                                src={imgSrc}
                                alt={ad.name}
                                className="ad-picker-thumb"
                              />
                            )}
                            <span className="ad-picker-name">{ad.name}</span>
                          </button>
                        );
                      })}
                    </div>
                  )}

                  <div className="ad-picker-actions">
                    <button
                      onClick={handleClearAd}
                      className="ad-picker-clear"
                    >
                      Χωρίς διαφήμιση
                      {selectionMode === "multi" && activeSelectionCount > 1
                        ? " (στις επιλεγμένες)"
                        : ""}
                    </button>
                    <button
                      onClick={() => {
                        setSelectedScreen(null);
                        setSelectedScreens([]);
                      }}
                      className="ad-picker-cancel"
                    >
                      Άκυρο επιλογής
                    </button>
                  </div>
                </div>
              )}
            </>
          ) : (
            <p>Διάλεξε μία ζώνη από αριστερά.</p>
          )}
        </section>
      </main>
    </div>
  );
}

export default VisualBoard;
