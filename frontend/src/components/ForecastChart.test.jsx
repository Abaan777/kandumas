import { describe, expect, it } from "vitest";
import { render } from "@testing-library/react";
import ForecastChart, { selectDisplayedForecast } from "./ForecastChart.jsx";

const PX_PER_MONTH = 34;
const HISTORY_WINDOW_MONTHS = 120;
const AXIS_COLUMN_PX = 56;

function point(month, catchKg) {
  return { month, catch_kg: catchKg, sst: 28, wind_speed: 4, salinity: 34 };
}

function monthsOfHistory(count, startYear = 2010) {
  return Array.from({ length: count }, (_, i) => {
    const year = startYear + Math.floor(i / 12);
    const month = String((i % 12) + 1).padStart(2, "0");
    return point(`${year}-${month}-01`, 1000 + i);
  });
}

describe("selectDisplayedForecast", () => {
  it("takes the LAST n points (the near-term months closest to today), not the first n", () => {
    const points = [
      { target_month: "2026-01-01" },
      { target_month: "2026-02-01" },
      { target_month: "2026-03-01" },
      { target_month: "2026-04-01" },
      { target_month: "2026-05-01" },
    ];
    expect(selectDisplayedForecast(points, 3).map((p) => p.target_month)).toEqual([
      "2026-03-01",
      "2026-04-01",
      "2026-05-01",
    ]);
  });

  it("returns everything available when there are fewer points than requested", () => {
    const points = [{ target_month: "2026-01-01" }];
    expect(selectDisplayedForecast(points, 3)).toEqual(points);
  });

  it("returns an empty list for an empty input", () => {
    expect(selectDisplayedForecast([], 3)).toEqual([]);
  });
});

describe("ForecastChart", () => {
  it("caps history at 10 years even when more is available, and shows only the last 3 forecast months", () => {
    const historicalPoints = monthsOfHistory(200); // way more than 10 years
    // The backend returns far more than 3 months (it extends to the current calendar
    // month + 2, which can be a dozen+ months past the model's data anchor) -- the
    // chart must take the *tail* of this list (the near-term months), not the head
    // (the earliest months right after the anchor).
    const forecastPoints = [
      { target_month: "2026-01-01", predicted_catch_kg: 100 },
      { target_month: "2026-02-01", predicted_catch_kg: 200 },
      { target_month: "2026-03-01", predicted_catch_kg: 300 },
      { target_month: "2026-04-01", predicted_catch_kg: 400 },
      { target_month: "2026-05-01", predicted_catch_kg: 500 },
    ];

    const { container } = render(
      <ForecastChart historicalPoints={historicalPoints} forecastPoints={forecastPoints} />
    );

    const scroll = container.querySelector(".chart-scroll");
    const scrollWrap = container.querySelector(".chart-scroll .chart-wrap");
    expect(scroll).toBeInTheDocument();
    // 120 months of history (not 200) + 3 forecast months (the last 3 of the 5 given).
    expect(scrollWrap.style.width).toBe(`${(HISTORY_WINDOW_MONTHS + 3) * PX_PER_MONTH}px`);
    expect(scrollWrap.style.minWidth).toBe("100%");
  });

  it("renders a fixed-width axis column outside the scrolling container", () => {
    const historicalPoints = monthsOfHistory(24);
    const forecastPoints = [{ target_month: "2026-07-01", predicted_catch_kg: 1200 }];

    const { container } = render(
      <ForecastChart historicalPoints={historicalPoints} forecastPoints={forecastPoints} />
    );

    const row = container.querySelector(".chart-fixed-row");
    const axisWrap = row.querySelector(":scope > .chart-wrap");
    expect(axisWrap).toBeInTheDocument();
    expect(axisWrap.style.width).toBe(`${AXIS_COLUMN_PX}px`);
    // Not inside .chart-scroll -- it must not move when the plot is scrolled.
    expect(container.querySelector(".chart-scroll").contains(axisWrap)).toBe(false);
  });

  it("doesn't pad width out when there's less than 10 years of history or fewer than 3 forecast months available", () => {
    const historicalPoints = monthsOfHistory(6);
    const forecastPoints = [{ target_month: "2026-07-01", predicted_catch_kg: 1200 }];

    const { container } = render(
      <ForecastChart historicalPoints={historicalPoints} forecastPoints={forecastPoints} />
    );

    const scrollWrap = container.querySelector(".chart-scroll .chart-wrap");
    expect(scrollWrap.style.width).toBe(`${(6 + 1) * PX_PER_MONTH}px`);
  });

  it("renders without crashing when there's no data yet", () => {
    const { container } = render(<ForecastChart historicalPoints={[]} forecastPoints={[]} />);
    const scrollWrap = container.querySelector(".chart-scroll .chart-wrap");
    expect(scrollWrap.style.width).toBe("0px");
  });
});
