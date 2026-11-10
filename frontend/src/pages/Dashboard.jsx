import { useEffect, useState } from "react";
import DailyEstimateCard, { friendlyDayLabel, todayISO } from "../components/DailyEstimateCard.jsx";
import FilterBar from "../components/FilterBar.jsx";
import ForecastChart from "../components/ForecastChart.jsx";
import RegionMap from "../components/RegionMap.jsx";
import {
  getDailyEstimate,
  getDashboardOverview,
  getHistorical,
  getRegionAccuracy,
  getRegions,
  postPredict,
} from "../api/client.js";

export default function Dashboard() {
  const [overview, setOverview] = useState(null);
  const [filters, setFilters] = useState({ region: "North Maldives", species: "Skipjack tuna" });
  const [monthsAhead, setMonthsAhead] = useState(3);
  const [historical, setHistorical] = useState([]);
  const [prediction, setPrediction] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [regions, setRegions] = useState([]);
  const [accuracyByRegion, setAccuracyByRegion] = useState({});
  // Mirrors the date picked in the Daily Catch Estimate card so the map can show that
  // same date's predicted catch per region, not just the one region the card covers.
  const [selectedDate, setSelectedDate] = useState(todayISO());
  const [dailyByRegion, setDailyByRegion] = useState({});
  const [mapDailyLoading, setMapDailyLoading] = useState(false);

  useEffect(() => {
    getDashboardOverview().then((res) => setOverview(res.data));
    getRegions().then((res) => setRegions(res.data));
  }, []);

  useEffect(() => {
    if (!filters.region || !filters.species) return;
    getHistorical({ region: filters.region, species: filters.species }).then((res) => setHistorical(res.data));
  }, [filters.region, filters.species]);

  // The map shows every region's accuracy for the currently chosen species (not just
  // the one region selected in the filter above), so a species change is enough to
  // refresh it -- no need to wait for "Generate Prediction".
  useEffect(() => {
    if (!filters.species) return;
    getRegionAccuracy(filters.species).then((res) => {
      const byRegion = {};
      res.data.forEach((r) => {
        byRegion[r.region] = r;
      });
      setAccuracyByRegion(byRegion);
    });
  }, [filters.species]);

  // One /predict/daily call per region for the currently selected date -- each region
  // has its own lat/lon, so the live weather forecast (and the resulting estimate) is
  // genuinely different per region and can't be fetched in a single request. Some
  // region/species combinations may have no trained Prophet model yet; those are left
  // out of the map rather than failing the whole update.
  useEffect(() => {
    if (!filters.species || !selectedDate || regions.length === 0) return;
    let cancelled = false;
    setMapDailyLoading(true);
    Promise.allSettled(regions.map((r) => getDailyEstimate(r.name, filters.species, selectedDate))).then(
      (results) => {
        if (cancelled) return;
        const byRegion = {};
        results.forEach((res, i) => {
          if (res.status === "fulfilled") {
            const day = res.value.data.days?.[0];
            if (day) byRegion[regions[i].name] = day;
          }
        });
        setDailyByRegion(byRegion);
        setMapDailyLoading(false);
      }
    );
    return () => {
      cancelled = true;
    };
  }, [filters.species, selectedDate, regions]);

  const handleGenerate = async () => {
    if (!filters.species) {
      setError("Choose a species first.");
      return;
    }
    setError("");
    setLoading(true);
    try {
      const { data } = await postPredict({
        region: filters.region,
        species: filters.species,
        months_ahead: Number(monthsAhead),
      });
      setPrediction(data);
    } catch (err) {
      setPrediction(null);
      setError(err.response?.data?.detail || "Could not generate a prediction for this combination yet.");
    } finally {
      setLoading(false);
    }
  };

  const maxForecast = prediction ? Math.max(...prediction.points.map((p) => p.predicted_catch_kg)) : null;
  const avgCatch = historical.length
    ? historical.reduce((sum, h) => sum + h.catch_kg, 0) / historical.length
    : null;
  const latestSst = historical.length ? [...historical].reverse().find((h) => h.sst != null)?.sst : null;

  // Real data gap: the environmental data (which the model is trained on) can lag
  // months/years behind the most recent catch records for a given region. When it
  // does, say so plainly instead of leaving the reader to wonder why the forecast
  // doesn't start "now".
  const latestCatchMonth = historical.length ? historical[historical.length - 1].month : null;
  const forecastLagsBehindCatchData =
    prediction && latestCatchMonth && prediction.points[0].target_month < latestCatchMonth;

  const mapRegions = regions.map((r) => {
    const acc = accuracyByRegion[r.name];
    const daily = dailyByRegion[r.name];
    return {
      ...r,
      value: daily?.estimated_catch_kg ?? null,
      favorabilityRatio: daily?.favorability_ratio ?? null,
      accuracyPct: acc?.accuracy_pct ?? null,
      modelName: acc?.model_name ?? null,
      rmse: acc?.rmse ?? null,
      mape: acc?.mape ?? null,
    };
  });

  return (
    <div className="page">
      <div className="card">
        <h2>Forecast Overview</h2>
        <FilterBar
          value={filters}
          onChange={setFilters}
          extra={
            <div className="filter-field">
              <label htmlFor="months-ahead">Months ahead</label>
              <input
                id="months-ahead"
                type="number"
                min={1}
                max={12}
                value={monthsAhead}
                onChange={(e) => setMonthsAhead(e.target.value)}
              />
            </div>
          }
        />
        <div style={{ marginTop: "1rem" }}>
          <button className="btn-primary" onClick={handleGenerate} disabled={loading}>
            {loading ? "Generating..." : "Generate Prediction"}
          </button>
        </div>
        {error && <p className="error-text">{error}</p>}
      </div>

      <DailyEstimateCard region={filters.region} species={filters.species} onDateChange={setSelectedDate} />

      <div className="two-col-grid">
        <div className="card">
          <h3>Predicted vs. Historical Catch</h3>
          <ForecastChart historicalPoints={historical} forecastPoints={prediction?.points || []} />
          {prediction && (
            <>
              <p className="helper-text" style={{ marginTop: "0.5rem" }}>
                Model used: <span className="badge badge-model">{prediction.model_used.toUpperCase()}</span>{" "}
                {prediction.rmse != null && (
                  <>
                    &nbsp;RMSE: {prediction.rmse.toFixed(1)} kg &nbsp;MAPE: {prediction.mape.toFixed(1)}%
                  </>
                )}
              </p>
              {forecastLagsBehindCatchData && (
                <p className="helper-text">
                  Forecast starts {prediction.points[0].target_month} -- the model's environmental data (SST/wind/salinity) for this region only extends that far, even though catch records go more recent.
                </p>
              )}
              {!filters.region && (
                <p className="helper-text">
                  This is the national model (all regions combined) -- pick a specific region above to also see its historical catch for comparison.
                </p>
              )}
            </>
          )}
        </div>

        <div className="card">
          <h3>Key Metrics</h3>
          <div className="metric-grid">
            <div className="metric-tile">
              <div className="label">Max forecast</div>
              <div className="value">{maxForecast != null ? `${Math.round(maxForecast).toLocaleString()} kg` : "-"}</div>
            </div>
            <div className="metric-tile">
              <div className="label">Avg catch (history)</div>
              <div className="value">{avgCatch != null ? `${Math.round(avgCatch).toLocaleString()} kg` : "-"}</div>
            </div>
            <div className="metric-tile">
              <div className="label">Latest SST</div>
              <div className="value">{latestSst != null ? `${latestSst.toFixed(1)} C` : "-"}</div>
            </div>
            <div className="metric-tile">
              <div className="label">Regions tracked</div>
              <div className="value">{overview?.total_regions ?? "-"}</div>
            </div>
          </div>
        </div>
      </div>

      <div className="card">
        <h3>Region Map</h3>
        <p className="helper-text" style={{ marginTop: "-0.5rem", fontWeight: 600 }}>
          Prediction for {friendlyDayLabel(selectedDate)} ({selectedDate}) -- pick a different date in the Daily
          Catch Estimate card above to update the map.
        </p>
        <p className="helper-text">
          Label shows each region's forecast accuracy for <strong>{filters.species || "the selected species"}</strong> (100% minus its best model's error relative to typical catch size). Marker color is a gradient:{" "}
          <span style={{ color: "rgb(199, 46, 46)", fontWeight: 600 }}>red</span> = most accurate,{" "}
          through <span style={{ color: "rgb(224, 194, 63)", fontWeight: 600 }}>yellow</span>,{" "}
          down to <span style={{ color: "rgb(58, 110, 165)", fontWeight: 600 }}>blue</span> = least accurate. Size reflects each region's predicted catch for the date above.
        </p>
        {mapDailyLoading && <p className="helper-text">Updating predictions for the selected date...</p>}
        <RegionMap regions={mapRegions} />
      </div>
    </div>
  );
}
