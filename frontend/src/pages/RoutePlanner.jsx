import { useState, useCallback, useEffect } from "react";
import { useLocation } from "react-router-dom";
import { MapPin, Navigation, RotateCcw, Clock, Route as RouteIcon, Info, Layers, CheckCircle2 } from "lucide-react";
import MapView from "../components/MapView.jsx";
import CongestionBadge from "../components/CongestionBadge.jsx";
import DemoModeBanner from "../components/DemoModeBanner.jsx";
import ErrorMessage from "../components/ErrorMessage.jsx";
import { LoadingSpinner } from "../components/Loading.jsx";
import { calculateRoutes } from "../services/api.js";

const QUICK_LOCATIONS = [
  { name: "MG Road", lat: 12.9756, lng: 77.6099 },
  { name: "Sony World (Koramangala)", lat: 12.9358, lng: 77.6292 },
  { name: "Silk Board Junction", lat: 12.9174, lng: 77.6228 },
  { name: "Indiranagar (100ft Rd)", lat: 12.9784, lng: 77.6408 },
  { name: "Forum Mall (Adugodi)", lat: 12.9345, lng: 77.6112 },
  { name: "Richmond Circle", lat: 12.9602, lng: 77.5975 },
  { name: "Lalbagh Botanical Garden", lat: 12.9507, lng: 77.5848 },
  { name: "Jayanagar 4th Block", lat: 12.9299, lng: 77.5833 },
  { name: "Tavarekere / BTM", lat: 12.9248, lng: 77.6136 },
  { name: "Koramangala 4th Block", lat: 12.9340, lng: 77.6230 },
  { name: "Madiwala Market", lat: 12.9215, lng: 77.6200 },
  { name: "Ejipura Signal", lat: 12.9426, lng: 77.6274 },
];

function parseCoords(text) {
  if (!text) return null;
  const parts = text.split(",").map(p => parseFloat(p.trim()));
  if (parts.length === 2 && !isNaN(parts[0]) && !isNaN(parts[1])) {
    if (parts[0] >= -90 && parts[0] <= 90 && parts[1] >= -180 && parts[1] <= 180) {
      return { lat: parts[0], lng: parts[1] };
    }
  }
  return null;
}

export default function RoutePlanner() {
  const location = useLocation();
  const stateData = location.state;

  const [source, setSource] = useState(
    stateData?.source || { lat: 12.93520, lng: 77.62450 } // Koramangala
  );
  const [destination, setDestination] = useState(
    stateData?.destination || { lat: 12.97560, lng: 77.60990 } // MG Road
  );

  const [sourceInput, setSourceInput] = useState(
    source ? `${source.lat.toFixed(5)}, ${source.lng.toFixed(5)}` : ""
  );
  const [destInput, setDestInput] = useState(
    destination ? `${destination.lat.toFixed(5)}, ${destination.lng.toFixed(5)}` : ""
  );

  const [selectingFor, setSelectingFor] = useState(null); // "source" | "destination" | null
  const [avoidCongestion, setAvoidCongestion] = useState(true);
  const [routes, setRoutes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [isDemoMode, setIsDemoMode] = useState(false);
  const [graphNote, setGraphNote] = useState("");
  const [demoWarning, setDemoWarning] = useState(null);
  const [selectedRouteIdx, setSelectedRouteIdx] = useState(0);
  const [snapDetails, setSnapDetails] = useState(null);

  const updateSource = useCallback((coord) => {
    setSource(coord);
    setSourceInput(coord ? `${coord.lat.toFixed(5)}, ${coord.lng.toFixed(5)}` : "");
  }, []);

  const updateDestination = useCallback((coord) => {
    setDestination(coord);
    setDestInput(coord ? `${coord.lat.toFixed(5)}, ${coord.lng.toFixed(5)}` : "");
  }, []);

  const handleMapClick = useCallback((coord, forField) => {
    if (forField === "source") updateSource(coord);
    else if (forField === "destination") updateDestination(coord);
    setSelectingFor(null);
  }, [updateSource, updateDestination]);

  const handleSourceInputChange = (val) => {
    setSourceInput(val);
    const parsed = parseCoords(val);
    if (parsed) setSource(parsed);
  };

  const handleDestInputChange = (val) => {
    setDestInput(val);
    const parsed = parseCoords(val);
    if (parsed) setDestination(parsed);
  };

  const handleSearch = async () => {
    if (!source || !destination) {
      setError("Please select both start and destination points.");
      return;
    }
    setLoading(true);
    setError(null);
    setRoutes([]);
    try {
      const data = await calculateRoutes(source, destination, avoidCongestion);
      setRoutes(data.routes || []);
      setIsDemoMode(data.is_demo_mode || false);
      setGraphNote(data.graph_note || "OpenStreetMap road network");
      setDemoWarning(data.warning || null);
      setSelectedRouteIdx(0);

      if (data.source_snapped && data.destination_snapped) {
        setSnapDetails({
          sourceSnapped: data.source_snapped,
          destSnapped: data.destination_snapped,
          sourceDist: data.source_snap_distance_m || 0,
          destDist: data.destination_snap_distance_m || 0,
        });
      }
    } catch (e) {
      const msg = e.response?.data?.detail || e.message || "Route calculation failed.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    updateSource(null);
    updateDestination(null);
    setRoutes([]);
    setError(null);
    setSelectingFor(null);
    setSnapDetails(null);
  };

  // Auto-search on initial load if source and destination are present
  useEffect(() => {
    if (source && destination && routes.length === 0) {
      handleSearch();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const selectedRoutes = routes.slice(0, 3);
  // Display routes with distinct colors, emphasizing the selected route with greater weight
  const displayRoutes = selectedRoutes.map((r, i) => ({
    ...r,
    color: r.color,
    weight: i === selectedRouteIdx ? 7 : 4,
    opacity: i === selectedRouteIdx ? 1.0 : 0.60,
  }));


  return (
    <div className="max-w-7xl mx-auto px-4 py-6 grid lg:grid-cols-[360px_1fr] gap-6">
      {/* Sidebar Controls */}
      <div className="space-y-4">
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-bold text-blue-900 flex items-center gap-2">
              <Navigation size={20} className="text-blue-600" /> A* Route Planner
            </h2>
            {!isDemoMode && routes.length > 0 && (
              <span className="flex items-center gap-1 text-[11px] font-semibold text-green-700 bg-green-50 px-2 py-0.5 rounded-full border border-green-200">
                <CheckCircle2 size={12} /> OSM Network
              </span>
            )}
          </div>

          {/* Source Input */}
          <div className="mb-3">
            <div className="flex items-center justify-between mb-1">
              <label className="text-xs font-semibold text-slate-500">START LOCATION (LAT, LNG)</label>
              {snapDetails && (
                <span className="text-[10px] text-blue-600 font-medium">
                  Road snap: {Math.round(snapDetails.sourceDist)}m
                </span>
              )}
            </div>
            <div className="flex gap-2">
              <input
                type="text"
                value={sourceInput}
                onChange={(e) => handleSourceInputChange(e.target.value)}
                placeholder="12.93520, 77.62450"
                className="flex-1 bg-blue-50/70 border border-blue-200 rounded-lg px-3 py-2 text-xs font-mono text-blue-900 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
              <button
                type="button"
                onClick={() => setSelectingFor(selectingFor === "source" ? null : "source")}
                className={`px-3 py-2 rounded-lg text-xs font-semibold transition-colors flex items-center gap-1 ${
                  selectingFor === "source" ? "bg-blue-600 text-white" : "bg-blue-100 text-blue-700 hover:bg-blue-200"
                }`}
                title="Click on map to pick"
              >
                <MapPin size={14} /> Map
              </button>
            </div>
          </div>

          {/* Destination Input */}
          <div className="mb-4">
            <div className="flex items-center justify-between mb-1">
              <label className="text-xs font-semibold text-slate-500">DESTINATION (LAT, LNG)</label>
              {snapDetails && (
                <span className="text-[10px] text-red-600 font-medium">
                  Road snap: {Math.round(snapDetails.destDist)}m
                </span>
              )}
            </div>
            <div className="flex gap-2">
              <input
                type="text"
                value={destInput}
                onChange={(e) => handleDestInputChange(e.target.value)}
                placeholder="12.97560, 77.60990"
                className="flex-1 bg-red-50/70 border border-red-200 rounded-lg px-3 py-2 text-xs font-mono text-red-900 focus:outline-none focus:ring-1 focus:ring-red-500"
              />
              <button
                type="button"
                onClick={() => setSelectingFor(selectingFor === "destination" ? null : "destination")}
                className={`px-3 py-2 rounded-lg text-xs font-semibold transition-colors flex items-center gap-1 ${
                  selectingFor === "destination" ? "bg-red-600 text-white" : "bg-red-100 text-red-700 hover:bg-red-200"
                }`}
                title="Click on map to pick"
              >
                <MapPin size={14} /> Map
              </button>
            </div>
          </div>

          {selectingFor && (
            <div className="bg-amber-50 text-amber-800 border border-amber-200 text-xs px-3 py-2 rounded-lg mb-3 flex items-center gap-2">
              <Info size={14} className="text-amber-600 flex-shrink-0" />
              <span>Click anywhere on the map to place <strong>{selectingFor}</strong>.</span>
            </div>
          )}

          {/* Quick Select Landmarks */}
          <div className="mb-4">
            <p className="text-xs font-semibold text-slate-500 mb-2">QUICK SELECT BENGALURU STOPS</p>
            <div className="grid grid-cols-2 gap-1.5 max-h-52 overflow-y-auto pr-1">
              {QUICK_LOCATIONS.map((loc) => (
                <div key={loc.name} className="flex gap-1">
                  <button
                    type="button"
                    onClick={() => updateSource({ lat: loc.lat, lng: loc.lng })}
                    className="flex-1 bg-blue-50 hover:bg-blue-100 text-blue-800 text-[11px] py-1 px-1.5 rounded text-left truncate border border-blue-100"
                    title={`Set ${loc.name} as start`}
                  >
                    🔵 {loc.name}
                  </button>
                  <button
                    type="button"
                    onClick={() => updateDestination({ lat: loc.lat, lng: loc.lng })}
                    className="flex-1 bg-red-50 hover:bg-red-100 text-red-800 text-[11px] py-1 px-1.5 rounded text-left truncate border border-red-100"
                    title={`Set ${loc.name} as destination`}
                  >
                    🔴 {loc.name}
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* Avoid Congestion Toggle */}
          <label className="flex items-center gap-2 mb-4 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={avoidCongestion}
              onChange={(e) => setAvoidCongestion(e.target.checked)}
              className="rounded accent-blue-600 h-4 w-4"
            />
            <span className="text-xs font-medium text-slate-700">
              Avoid traffic bottlenecks (A* congestion cost)
            </span>
          </label>

          {/* Action Buttons */}
          <div className="flex gap-2">
            <button
              onClick={handleSearch}
              disabled={loading || !source || !destination}
              className="flex-1 btn-primary flex items-center justify-center gap-2 py-2 text-sm"
            >
              {loading ? "Searching Streets..." : <><Navigation size={15} /> Find Real Routes</>}
            </button>
            <button
              onClick={handleReset}
              className="btn-secondary px-3"
              title="Reset locations"
            >
              <RotateCcw size={15} />
            </button>
          </div>
        </div>

        {/* Error message */}
        {error && <ErrorMessage message={error} onRetry={handleSearch} />}

        {/* Loading state */}
        {loading && <LoadingSpinner message="Calculating street paths with A*..." />}

        {/* Demo banner only if real graph failed to load */}
        {isDemoMode && (
          <DemoModeBanner
            message={demoWarning || "Using demo fallback. OpenStreetMap driving road network was not loaded."}
          />
        )}

        {/* Calculated Routes Cards */}
        {routes.length > 0 && (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs text-slate-500 font-semibold px-1">
              <span>{routes.length} Street Route{routes.length > 1 ? "s" : ""} Found</span>
              <span className="text-blue-600 flex items-center gap-1">
                <Layers size={12} /> {graphNote}
              </span>
            </div>

            {routes.map((route, i) => (
              <button
                key={route.route_id || i}
                onClick={() => setSelectedRouteIdx(i)}
                className={`w-full text-left card p-3.5 transition-all border-2 ${
                  selectedRouteIdx === i
                    ? "border-blue-600 shadow-md bg-blue-50/20"
                    : "border-slate-200 hover:border-slate-300"
                }`}
              >
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center gap-2">
                    <div
                      className="w-3.5 h-3.5 rounded-full shadow-sm flex-shrink-0"
                      style={{ background: route.color }}
                    />
                    <div className="flex items-center gap-1.5">
                      <span className="font-bold text-sm text-slate-800">{route.label}</span>
                    </div>
                  </div>
                  {route.congestion_level && <CongestionBadge level={route.congestion_level} />}
                </div>

                {route.recommendation_reason && (
                  <p className="text-[11px] text-slate-600 bg-slate-100/70 p-1.5 rounded mb-2 leading-relaxed border border-slate-200/60">
                    {route.recommendation_reason}
                  </p>
                )}

                <div className="grid grid-cols-2 gap-2 text-xs text-slate-600 mb-2 bg-slate-50 rounded-lg p-2">
                  <span className="flex items-center gap-1 font-medium">
                    <RouteIcon size={12} className="text-slate-400" />
                    {route.total_distance_km} km
                  </span>
                  <span className="flex items-center gap-1 font-medium">
                    <Clock size={12} className="text-slate-400" />
                    {route.total_time_min} mins
                  </span>
                </div>

                {/* Congestion breakdown bar */}
                {route.congestion_breakdown && (
                  <div className="space-y-1 mb-2">
                    <div className="flex items-center justify-between text-[10px] text-slate-500 font-medium">
                      <span>Segment Congestion</span>
                      <span className="font-mono text-[9px]">Score: {route.congestion_score?.toFixed(2) || "N/A"}</span>
                    </div>
                    <div className="w-full h-2 rounded-full overflow-hidden flex bg-slate-100">
                      <div
                        style={{ width: `${route.congestion_breakdown.LOW}%` }}
                        className="bg-emerald-500 h-full"
                        title={`Low: ${route.congestion_breakdown.LOW}%`}
                      />
                      <div
                        style={{ width: `${route.congestion_breakdown.MEDIUM}%` }}
                        className="bg-amber-400 h-full"
                        title={`Medium: ${route.congestion_breakdown.MEDIUM}%`}
                      />
                      <div
                        style={{ width: `${route.congestion_breakdown.HIGH}%` }}
                        className="bg-rose-500 h-full"
                        title={`Hard: ${route.congestion_breakdown.HIGH}%`}
                      />
                    </div>
                    <div className="flex items-center justify-between text-[10px] text-slate-500 font-mono px-0.5">
                      <span className="text-emerald-700">Low {route.congestion_breakdown.LOW}%</span>
                      <span className="text-amber-700">Med {route.congestion_breakdown.MEDIUM}%</span>
                      <span className="text-rose-700">Hard {route.congestion_breakdown.HIGH}%</span>
                    </div>
                  </div>
                )}

                <div className="flex items-center justify-between text-[11px] text-slate-400 pt-1 border-t border-slate-100">
                  <span>{route.segments?.length || route.geometry?.length || 0} road segments</span>
                  <span className="text-blue-600 font-medium">Click to select</span>
                </div>
              </button>
            ))}

            {/* Map Legend */}
            <div className="card p-3 text-xs text-slate-500 space-y-1.5">
              <p className="font-semibold text-slate-700">Map Legend</p>
              <p className="flex items-center gap-1.5">🔵 <span>Start location marker</span></p>
              <p className="flex items-center gap-1.5">🔴 <span>Destination marker</span></p>
              <p className="flex items-center gap-1.5"><span className="w-3 h-1 bg-blue-600 rounded"></span> <span>Route 1 driving path</span></p>
              <p className="flex items-center gap-1.5"><span className="w-3 h-1 bg-green-600 rounded"></span> <span>Route 2 street path</span></p>
              <p className="flex items-center gap-1.5"><span className="w-3 h-1 bg-amber-600 rounded"></span> <span>Route 3 street path</span></p>
            </div>

            {/* Transparent Diagnostics & Model Attribution Note */}
            <div className="card p-3 text-[11px] text-slate-500 space-y-1.5 border border-slate-200/80 bg-slate-50/50">
              <p className="font-semibold text-slate-700 flex items-center gap-1">
                <Info size={13} className="text-blue-600" /> Route Optimization & Model Transparency
              </p>
              <p className="leading-relaxed">
                Segment congestion is computed by the trained <strong>Random Forest model</strong> (90.2% test accuracy) from physical road attributes and historical Bengaluru traffic patterns.
              </p>
              <p className="text-[10px] text-slate-400">
                Rule: Classified by dominant segment congestion percentage (whichever of Low, Medium, or Hard is highest). Routes ordered as Route 1, Route 2, Route 3.
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Interactive Map */}
      <div className="space-y-3">
        <MapView
          center={[12.9500, 77.6150]}
          zoom={13}
          source={source}
          destination={destination}
          routes={displayRoutes}
          onMapClick={handleMapClick}
          selectingFor={selectingFor}
          className="h-[calc(100vh-10rem)] min-h-[500px]"
        />

        {selectingFor && (
          <div className="bg-blue-600 text-white text-sm px-4 py-2 rounded-lg text-center font-medium shadow-sm animate-pulse">
            Click on the map to set <strong>{selectingFor}</strong>
          </div>
        )}
      </div>
    </div>
  );
}