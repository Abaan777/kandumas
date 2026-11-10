import { useEffect, useState } from "react";
import { getDailyEstimate } from "../api/client.js";

const MAX_DAYS_AHEAD = 7; // today through 6 days ahead -- matches the backend's cap

function toISODate(d) {
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function todayISO() {
  return toISODate(new Date());
}

export function maxDateISO() {
  const d = new Date();
  d.setDate(d.getDate() + MAX_DAYS_AHEAD - 1);
  return toISODate(d);
}

export function friendlyDayLabel(dateStr) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const target = new Date(`${dateStr}T00:00:00`);
  const diffDays = Math.round((target - today) / 86400000);
  if (diffDays === 0) return "Today";
  if (diffDays === 1) return "Tomorrow";
  return target.toLocaleDateString("en", { weekday: "long" });
}

function favorabilityLabel(ratio) {
  if (ratio == null) return { text: "Unknown", color: "#9aa5a3" };
  if (ratio >= 1.15) return { text: "Favorable", color: "#2fa876" };
  if (ratio <= 0.85) return { text: "Unfavorable", color: "#c0392b" };
  return { text: "Average", color: "#e0a83f" };
}

export default function DailyEstimateCard({ region, species, onDateChange }) {
  const [selectedDate, setSelectedDate] = useState(todayISO());
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // Lets the dashboard mirror this date onto the Region Map (which fetches a daily
  // estimate per region, not just the one selected here) without making this card a
  // fully controlled component -- it still owns and defaults its own date.
  useEffect(() => {
    onDateChange?.(selectedDate);
  }, [selectedDate, onDateChange]);

  useEffect(() => {
    if (!region || !species || !selectedDate) return;
    setLoading(true);
    setError("");
    setData(null);
    getDailyEstimate(region, species, selectedDate)
      .then((res) => setData(res.data))
      .catch((err) => setError(err.response?.data?.detail || "Could not fetch a daily estimate right now."))
      .finally(() => setLoading(false));
  }, [region, species, selectedDate]);

  const day = data?.days?.[0];
  const fav = day ? favorabilityLabel(day.favorability_ratio) : null;

  return (
    <div className="card">
      <h3>Daily Catch Estimate</h3>
      <div className="filter-field" style={{ marginBottom: "1rem", maxWidth: "220px" }}>
        <label htmlFor="daily-estimate-date">Pick a date (up to 7 days ahead)</label>
        <input
          id="daily-estimate-date"
          type="date"
          value={selectedDate}
          min={todayISO()}
          max={maxDateISO()}
          onChange={(e) => setSelectedDate(e.target.value)}
        />
      </div>

      {loading && <p className="helper-text">Fetching live weather and building the estimate...</p>}
      {error && <p className="error-text">{error}</p>}
      {day && (
        <>
          <div className="daily-grid">
            <div className="daily-tile">
              <div className="daily-tile-label">{friendlyDayLabel(day.date)}</div>
              <div className="daily-tile-date">{day.date}</div>
              <div className="daily-tile-value">
                {day.estimated_catch_kg != null ? `${Math.round(day.estimated_catch_kg).toLocaleString()} kg` : "-"}
              </div>
              <div className="daily-tile-badge" style={{ color: fav.color, borderColor: fav.color }}>
                {fav.text}
              </div>
              <div className="daily-tile-conditions">
                {day.sst != null ? `${day.sst.toFixed(1)} C` : "SST n/a"}
                {" · "}
                {day.wind_speed != null ? `${day.wind_speed.toFixed(1)} m/s` : "wind n/a"}
              </div>
            </div>
          </div>
          <p className="helper-text" style={{ marginTop: "0.85rem" }}>{data.disclaimer}</p>
        </>
      )}
    </div>
  );
}
