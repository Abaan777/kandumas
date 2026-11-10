import { useEffect, useState } from "react";
import { getAdminMetrics, refreshDatasets, retrainModels } from "../api/client.js";

export default function Admin() {
  const [metrics, setMetrics] = useState([]);
  const [status, setStatus] = useState("");
  const [loadingAction, setLoadingAction] = useState(null);

  const loadMetrics = () => {
    getAdminMetrics().then((res) => setMetrics(res.data));
  };

  useEffect(() => {
    loadMetrics();
  }, []);

  const runAction = async (action, fn, message) => {
    setLoadingAction(action);
    setStatus("");
    try {
      const { data } = await fn();
      setStatus(data.detail || message);
    } catch (err) {
      setStatus(err.response?.data?.detail || "Action failed.");
    } finally {
      setLoadingAction(null);
    }
  };

  return (
    <div className="page">
      <div className="card">
        <h2>Admin - Data Management</h2>
        <p className="helper-text">
          Datasets are fetched live from FAO/IOTC/NOAA rather than manually uploaded (see
          docs/DATA_SOURCES.md) -- use the actions below to re-pull the latest data and
          retrain the forecasting models.
        </p>
        <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
          <button
            className="btn-primary"
            disabled={loadingAction !== null}
            onClick={() =>
              runAction("refresh", refreshDatasets, "Dataset refresh started in the background.")
            }
          >
            {loadingAction === "refresh" ? "Starting..." : "Refresh Datasets"}
          </button>
          <button
            className="btn-primary"
            disabled={loadingAction !== null}
            onClick={() => runAction("retrain", retrainModels, "Retraining started in the background.")}
          >
            {loadingAction === "retrain" ? "Starting..." : "Retrain Model"}
          </button>
          <button className="btn-secondary" onClick={loadMetrics}>
            Refresh Metrics Table
          </button>
        </div>
        {status && <p className="helper-text" style={{ marginTop: "0.75rem" }}>{status}</p>}
      </div>

      <div className="card">
        <h3>Model Performance (RMSE / MAPE)</h3>
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>Model</th>
                <th>Species</th>
                <th>Region</th>
                <th>RMSE (kg)</th>
                <th>MAPE (%)</th>
                <th>Best?</th>
                <th>Trained at</th>
              </tr>
            </thead>
            <tbody>
              {metrics.map((m, idx) => (
                <tr key={idx}>
                  <td>
                    <span className="badge badge-model">{m.model_name.toUpperCase()}</span>
                  </td>
                  <td>{m.species}</td>
                  <td>{m.region || "National"}</td>
                  <td>{m.rmse.toFixed(1)}</td>
                  <td>{m.mape.toFixed(1)}</td>
                  <td>{m.is_best && <span className="badge badge-best">BEST</span>}</td>
                  <td>{new Date(m.trained_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {metrics.length === 0 && <p className="helper-text">No model runs recorded yet -- train the models first.</p>}
      </div>
    </div>
  );
}
