import { useState } from "react";
import FilterBar from "../components/FilterBar.jsx";
import { downloadReport } from "../api/client.js";

export default function Reports() {
  const [filters, setFilters] = useState({ region: "North Maldives", species: "Skipjack tuna" });
  const [monthsAhead, setMonthsAhead] = useState(3);
  const [format, setFormat] = useState("csv");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState([]);

  const handleDownload = async () => {
    if (!filters.region || !filters.species) {
      setError("Choose both a region and a species first.");
      return;
    }
    setError("");
    setLoading(true);
    try {
      const response = await downloadReport({
        region: filters.region,
        species: filters.species,
        months_ahead: monthsAhead,
        file_format: format,
      });
      const blob = new Blob([response.data]);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      const filename = `kandumas_report_${filters.region}_${filters.species}.${format}`.replace(/\s+/g, "_");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      setHistory((h) => [{ region: filters.region, species: filters.species, format, at: new Date().toLocaleString() }, ...h]);
    } catch (err) {
      setError(err.response?.data?.detail || "Could not generate that report (model may not be trained yet).");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page">
      <div className="card">
        <h2>Reports</h2>
        <p className="helper-text">
          Download a forecast summary (predicted catch + recent historical/environmental data) as CSV or PDF.
        </p>
        <FilterBar
          value={filters}
          onChange={setFilters}
          extra={
            <>
              <div className="filter-field">
                <label htmlFor="report-months">Months ahead</label>
                <input
                  id="report-months"
                  type="number"
                  min={1}
                  max={12}
                  value={monthsAhead}
                  onChange={(e) => setMonthsAhead(e.target.value)}
                />
              </div>
              <div className="filter-field">
                <label htmlFor="report-format">Format</label>
                <select id="report-format" value={format} onChange={(e) => setFormat(e.target.value)}>
                  <option value="csv">CSV</option>
                  <option value="pdf">PDF</option>
                </select>
              </div>
            </>
          }
        />
        <div style={{ marginTop: "1rem" }}>
          <button className="btn-primary" onClick={handleDownload} disabled={loading}>
            {loading ? "Preparing..." : "Download Report"}
          </button>
        </div>
        {error && <p className="error-text">{error}</p>}
      </div>

      <div className="card">
        <h3>Generated this session</h3>
        {history.length === 0 && <p className="helper-text">No reports generated yet.</p>}
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>When</th>
                <th>Region</th>
                <th>Species</th>
                <th>Format</th>
              </tr>
            </thead>
            <tbody>
              {history.map((h, idx) => (
                <tr key={idx}>
                  <td>{h.at}</td>
                  <td>{h.region}</td>
                  <td>{h.species}</td>
                  <td>{h.format.toUpperCase()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
