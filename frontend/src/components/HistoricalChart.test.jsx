import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import HistoricalChart from "./HistoricalChart.jsx";

function point(month, wind) {
  return { month, catch_kg: 1000, sst: 28, wind_speed: wind, salinity: 34 };
}

describe("HistoricalChart", () => {
  it("shows no coverage note when the variable has data through the latest month", () => {
    const points = [point("2025-01-01", 4.1), point("2025-02-01", 4.3)];
    render(<HistoricalChart points={points} variable="wind_speed" label="Wind speed" />);
    expect(screen.queryByText(/data available through/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/no wind speed data available/i)).not.toBeInTheDocument();
  });

  it("explains a trailing data gap instead of silently stopping the line", () => {
    const points = [point("2023-05-01", 4.1), point("2023-06-01", 4.3), point("2023-07-01", null), point("2025-12-01", null)];
    render(<HistoricalChart points={points} variable="wind_speed" label="Wind speed" />);
    expect(screen.getByText(/Wind speed data available through Jun 2023/i)).toBeInTheDocument();
  });

  it("reports when there is no data at all for the variable in the window", () => {
    const points = [point("2025-01-01", null), point("2025-02-01", null)];
    render(<HistoricalChart points={points} variable="wind_speed" label="Wind speed" />);
    expect(screen.getByText(/No wind speed data available for this period/i)).toBeInTheDocument();
  });
});
