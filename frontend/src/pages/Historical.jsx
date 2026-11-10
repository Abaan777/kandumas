import { useEffect, useState } from "react";
import FilterBar from "../components/FilterBar.jsx";
import HistoricalChart from "../components/HistoricalChart.jsx";
import { getHistorical } from "../api/client.js";

export default function Historical() {
  const [filters, setFilters] = useState({ region: "North Maldives", species: "Skipjack tuna" });
  const [points, setPoints] = useState([]);

  useEffect(() => {
    const params = {};
    if (filters.region) params.region = filters.region;
    if (filters.species) params.species = filters.species;
    getHistorical(params).then((res) => setPoints(res.data));
  }, [filters.region, filters.species]);

  return (
    <div className="page">
      <div className="card">
        <h2>Historical Data &amp; Trends</h2>
        <FilterBar value={filters} onChange={setFilters} />
      </div>

      <div className="card">
        <h3>Catch Volume</h3>
        <p className="helper-text" style={{ marginTop: "-0.5rem" }}>Last 3 years shown for readability -- full history is in the table below.</p>
        <HistoricalChart points={points} variable="catch_kg" label="Catch" color="#1f6f8b" unit=" kg" />
      </div>

      <div className="trio-grid">
        <div className="card">
          <h3>Sea Surface Temperature</h3>
          <HistoricalChart points={points} variable="sst" label="SST" color="#e07a3f" unit=" C" />
        </div>
        <div className="card">
          <h3>Wind Speed</h3>
          <HistoricalChart points={points} variable="wind_speed" label="Wind speed" color="#7a5cc2" unit=" m/s" />
        </div>
        <div className="card">
          <h3>Salinity</h3>
          <HistoricalChart points={points} variable="salinity" label="Salinity" color="#2fa876" unit=" PSU" />
        </div>
      </div>

      <div className="card">
        <h3>Data Table</h3>
        <p className="helper-text" style={{ marginTop: "-0.5rem" }}>Most recent 24 months.</p>
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>Month</th>
                <th>Region</th>
                <th>Species</th>
                <th>Catch (kg)</th>
                <th>SST (C)</th>
                <th>Wind (m/s)</th>
                <th>Salinity (PSU)</th>
              </tr>
            </thead>
            <tbody>
              {points.slice(-24).map((p, idx) => (
                <tr key={idx}>
                  <td>{p.month}</td>
                  <td>{p.region}</td>
                  <td>{p.species}</td>
                  <td>{Math.round(p.catch_kg).toLocaleString()}</td>
                  <td>{p.sst != null ? p.sst.toFixed(2) : "-"}</td>
                  <td>{p.wind_speed != null ? p.wind_speed.toFixed(2) : "-"}</td>
                  <td>{p.salinity != null ? p.salinity.toFixed(2) : "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {points.length === 0 && <p className="helper-text">No data for this filter combination.</p>}
        </div>
      </div>
    </div>
  );
}
