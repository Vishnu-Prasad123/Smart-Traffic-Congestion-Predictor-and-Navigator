import { useEffect } from "react";
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap, useMapEvents } from "react-leaflet";
import L from "leaflet";

// Fix Leaflet default marker icons for Vite builds
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

const SOURCE_ICON = new L.Icon({
  iconUrl: "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-blue.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

const DEST_ICON = new L.Icon({
  iconUrl: "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

function MapClickHandler({ onMapClick, selectingFor }) {
  useMapEvents({
    click(e) {
      if (selectingFor && onMapClick) {
        onMapClick({ lat: e.latlng.lat, lng: e.latlng.lng }, selectingFor);
      }
    },
  });
  return null;
}

// Automatically fit map viewport to the calculated route geometry
function RouteBoundsFitter({ routes, source, destination }) {
  const map = useMap();

  useEffect(() => {
    if (!map) return;

    const points = [];
    if (routes && routes.length > 0) {
      routes.forEach((r) => {
        if (r.geometry && r.geometry.length > 0) {
          r.geometry.forEach((pt) => {
            if (Array.isArray(pt) && pt.length === 2 && !isNaN(pt[0]) && !isNaN(pt[1])) {
              points.push(pt);
            }
          });
        }
      });
    }

    if (points.length >= 2) {
      const bounds = L.latLngBounds(points);
      map.fitBounds(bounds, { padding: [45, 45], maxZoom: 16 });
    } else if (source && destination) {
      const bounds = L.latLngBounds([
        [source.lat, source.lng],
        [destination.lat, destination.lng],
      ]);
      map.fitBounds(bounds, { padding: [60, 60], maxZoom: 15 });
    } else if (source) {
      map.setView([source.lat, source.lng], 14);
    }
  }, [routes, source, destination, map]);

  return null;
}

export default function MapView({
  center = [12.9352, 77.6245],
  zoom = 14,
  source,
  destination,
  routes = [],
  onMapClick,
  selectingFor,
  className = "h-96",
}) {
  return (
    <div className={`rounded-xl overflow-hidden border border-slate-200 relative ${className}`}>
      <MapContainer
        center={center}
        zoom={zoom}
        style={{ height: "100%", width: "100%" }}
        scrollWheelZoom={true}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        <MapClickHandler onMapClick={onMapClick} selectingFor={selectingFor} />
        <RouteBoundsFitter routes={routes} source={source} destination={destination} />

        {/* Source Marker */}
        {source && (
          <Marker position={[source.lat, source.lng]} icon={SOURCE_ICON}>
            <Popup>
              <strong>Start / Origin</strong>
              <br />
              {source.lat.toFixed(5)}, {source.lng.toFixed(5)}
            </Popup>
          </Marker>
        )}

        {/* Destination Marker */}
        {destination && (
          <Marker position={[destination.lat, destination.lng]} icon={DEST_ICON}>
            <Popup>
              <strong>Destination</strong>
              <br />
              {destination.lat.toFixed(5)}, {destination.lng.toFixed(5)}
            </Popup>
          </Marker>
        )}

        {/* Real road network routes */}
        {routes.map((route, i) => (
          route.geometry && route.geometry.length > 1 && (
            <Polyline
              key={route.route_id || i}
              positions={route.geometry}
              pathOptions={{
                color: route.color || (i === 0 ? "#2563EB" : "#16A34A"),
                weight: route.weight || (i === 0 ? 6 : 4),
                opacity: i === 0 ? 0.95 : 0.70,
                lineJoin: "round",
                lineCap: "round",
              }}
            >
              <Popup>
                <div className="text-xs">
                  <strong className="text-sm">{route.label}</strong>
                  <br />
                  <span>Distance: <strong>{route.total_distance_km} km</strong></span>
                  <br />
                  <span>Est. Time: <strong>{route.total_time_min} min</strong></span>
                  {route.congestion_level && (
                    <div className="mt-1">
                      Congestion: <strong>{route.congestion_level === "HIGH" || route.congestion_level === "HARD" ? "Hard" : (route.congestion_level === "MEDIUM" ? "Medium" : "Low")}</strong>
                    </div>
                  )}
                  <div className="text-[10px] text-slate-400 mt-1">
                    {route.geometry.length} road coordinates
                  </div>
                </div>
              </Popup>
            </Polyline>
          )
        ))}
      </MapContainer>
    </div>
  );
}