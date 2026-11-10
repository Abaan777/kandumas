import { useEffect, useState } from "react";
import { getRegions, getSpecies } from "../api/client";

export default function FilterBar({ value, onChange, extra }) {
  const [regions, setRegions] = useState([]);
  const [species, setSpecies] = useState([]);

  useEffect(() => {
    getRegions().then((res) => setRegions(res.data));
    getSpecies().then((res) => setSpecies(res.data));
  }, []);

  const update = (field, val) => onChange({ ...value, [field]: val });

  return (
    <div className="filter-bar">
      <div className="filter-field">
        <label htmlFor="region-filter">Region</label>
        <select id="region-filter" value={value.region || ""} onChange={(e) => update("region", e.target.value)}>
          <option value="">All regions</option>
          {regions.map((r) => (
            <option key={r.id} value={r.name}>
              {r.name}
            </option>
          ))}
        </select>
      </div>
      <div className="filter-field">
        <label htmlFor="species-filter">Species</label>
        <select id="species-filter" value={value.species || ""} onChange={(e) => update("species", e.target.value)}>
          <option value="">All species</option>
          {species.map((s) => (
            <option key={s.id} value={s.name}>
              {s.name}
            </option>
          ))}
        </select>
      </div>
      {extra}
    </div>
  );
}
