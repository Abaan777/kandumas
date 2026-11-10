import { MapContainer, TileLayer, CircleMarker, Popup, Tooltip } from "react-leaflet";

// Maldives-centered map. Marker size reflects each region's predicted catch for the
// currently selected date (from the Daily Catch Estimate card above, one /predict/daily
// call per region) and marker color reflects forecast accuracy for the selected species
// (100 - MAPE, see prediction_service.get_region_accuracy) -- a permanent label on each
// marker shows the accuracy percentage directly, no click needed.
const HEAT_STOPS = [
  { pct: 0, rgb: [58, 110, 165] }, // blue -- least accurate
  { pct: 25, rgb: [47, 168, 118] }, // green
  { pct: 50, rgb: [224, 194, 63] }, // yellow
  { pct: 75, rgb: [224, 122, 63] }, // orange
  { pct: 100, rgb: [199, 46, 46] }, // red -- most accurate
];

function lerp(a, b, t) {
  return a + (b - a) * t;
}

function heatColor(pct) {
  if (pct == null) return "rgb(154, 165, 163)"; // no trained model / no data yet -- neutral gray
  const clamped = Math.max(0, Math.min(100, pct));
  for (let i = 0; i < HEAT_STOPS.length - 1; i++) {
    const a = HEAT_STOPS[i];
    const b = HEAT_STOPS[i + 1];
    if (clamped >= a.pct && clamped <= b.pct) {
      const t = (clamped - a.pct) / (b.pct - a.pct);
      const [r, g, bch] = a.rgb.map((channel, idx) => Math.round(lerp(channel, b.rgb[idx], t)));
      return `rgb(${r}, ${g}, ${bch})`;
    }
  }
  return `rgb(${HEAT_STOPS[HEAT_STOPS.length - 1].rgb.join(", ")})`;
}

export { heatColor };

export default function RegionMap({ regions = [] }) {
  const center = [3.2, 73.2];

  return (
    <div className="map-wrap">
      <MapContainer center={center} zoom={6} style={{ height: "100%", width: "100%" }}>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {regions.map((r) => {
          const color = heatColor(r.accuracyPct);
          return (
            <CircleMarker
              key={r.name}
              center={[r.lat_center, r.lon_center]}
              radius={Math.min(10 + (r.value || 0) / 5000, 30)}
              pathOptions={{ color, fillColor: color, fillOpacity: 0.55 }}
            >
              <Tooltip direction="top" offset={[0, -6]} permanent>
                {r.accuracyPct != null ? `${r.accuracyPct.toFixed(0)}% accurate` : "No model yet"}
              </Tooltip>
              <Popup>
                <strong>{r.name}</strong>
                <br />
                Location: {r.lat_center.toFixed(3)}&deg;N, {r.lon_center.toFixed(3)}&deg;E
                <br />
                {r.value != null
                  ? `Predicted catch (selected date): ${Math.round(r.value).toLocaleString()} kg`
                  : "No prediction for this date yet"}
                <br />
                {r.accuracyPct != null ? (
                  <>
                    Accuracy: {r.accuracyPct.toFixed(1)}% ({r.modelName?.toUpperCase()})
                    <br />
                    RMSE: {r.rmse != null ? `${Math.round(r.rmse).toLocaleString()} kg` : "-"}, MAPE:{" "}
                    {r.mape != null ? `${r.mape.toFixed(1)}%` : "-"}
                  </>
                ) : (
                  "No trained model for this species/region yet"
                )}
              </Popup>
            </CircleMarker>
          );
        })}
      </MapContainer>
    </div>
  );
}
