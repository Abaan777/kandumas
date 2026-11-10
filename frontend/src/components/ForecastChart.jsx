import { useEffect, useRef } from "react";
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend } from "chart.js";
import { Line } from "react-chartjs-2";
import { baseLineOptions, compactNumber, formatMonthLabel, lastNMonths } from "./chartUtils.js";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend);

// The card itself stays a fixed size -- the chart's drawing area inside it is wider
// than that frame (one fixed pixel width per month) and scrolls horizontally, so
// history doesn't have to be squeezed to fit. History goes back up to 10 years;
// prediction shows the current month plus the 2 after it.
const HISTORY_WINDOW_MONTHS = 120;
const FORECAST_DISPLAY_MONTHS = 3;
const PX_PER_MONTH = 34;
const AXIS_COLUMN_PX = 56;

// The backend always extends far enough to reach the current calendar month plus a
// couple more (see prediction_service.py's MONTHS_BEYOND_CURRENT) -- this chart only
// draws that near-term tail: the *last* few returned points, not the first few, which
// are the earliest months right after the model's data anchor, not "now". Exported so
// this exact slicing direction (easy to get backwards -- it already was once) is
// covered by a test that doesn't depend on reading Chart.js's own canvas output.
export function selectDisplayedForecast(forecastPoints, count = FORECAST_DISPLAY_MONTHS) {
  return forecastPoints.slice(-count);
}

export default function ForecastChart({ historicalPoints = [], forecastPoints = [] }) {
  const scrollRef = useRef(null);

  // The forecast picks up right after the last month the model actually had
  // environmental data for, which can lag behind the most recent catch records (real
  // data gaps -- see docs/DATA_SOURCES.md). Anchoring the history window there (rather
  // than at "today") keeps the two series in correct chronological order instead of
  // the forecast appearing to jump backwards on the axis.
  const anchorMonth = forecastPoints[0]?.target_month;
  const historyUpToAnchor = anchorMonth
    ? historicalPoints.filter((p) => p.month < anchorMonth)
    : historicalPoints;
  const recentHistory = lastNMonths(historyUpToAnchor, HISTORY_WINDOW_MONTHS);
  const shownForecast = selectDisplayedForecast(forecastPoints);

  const historicalLabels = recentHistory.map((p) => formatMonthLabel(p.month));
  const forecastLabels = shownForecast.map((p) => formatMonthLabel(p.target_month));
  const labels = [...historicalLabels, ...forecastLabels];

  const historicalData = recentHistory.map((p) => p.catch_kg);
  const forecastData = [
    ...new Array(Math.max(recentHistory.length - 1, 0)).fill(null),
    recentHistory.length ? recentHistory[recentHistory.length - 1].catch_kg : null,
    ...shownForecast.map((p) => p.predicted_catch_kg),
  ];

  const datasets = [
    {
      label: "Historical",
      data: [...historicalData, ...new Array(shownForecast.length).fill(null)],
      borderColor: "#1f6f8b",
      backgroundColor: "#1f6f8b22",
      tension: 0.3,
      fill: true,
    },
    {
      label: "Predicted",
      data: forecastData,
      borderColor: "#2fa876",
      borderDash: [6, 4],
      backgroundColor: "#2fa87622",
      tension: 0.3,
    },
  ];

  const data = { labels, datasets };

  const plotOptions = {
    ...baseLineOptions,
    scales: {
      ...baseLineOptions.scales,
      x: {
        ...baseLineOptions.scales.x,
        // Every month gets its own label (the shared default thins these out to ~7
        // for charts that don't scroll) -- rotated so "Jan 2026"-width text doesn't
        // overlap its neighbors at a per-month pixel budget this tight.
        ticks: { ...baseLineOptions.scales.x.ticks, autoSkip: false, maxRotation: 60, minRotation: 60 },
      },
      // The y-axis itself is drawn by the separate, non-scrolling chart below instead
      // (see axisData/axisOptions) -- this one keeps its gridlines (so the scrolled
      // plot still has horizontal reference lines) but hides its own tick labels so
      // they aren't duplicated/misaligned against the frozen ones.
      y: { ...baseLineOptions.scales.y, ticks: { ...baseLineOptions.scales.y.ticks, display: false } },
    },
    plugins: {
      legend: {
        display: true,
        position: "top",
        align: "start",
        labels: { boxWidth: 14, boxHeight: 14, usePointStyle: true, pointStyle: "line" },
      },
      tooltip: {
        callbacks: {
          label: (ctx) => `${ctx.dataset.label}: ${compactNumber(ctx.parsed.y)} kg`,
        },
      },
    },
  };

  // A second, narrow chart plotted on the exact same data (so Chart.js computes the
  // same y min/max and tick steps) but with every line/point made invisible and its
  // x-axis hidden -- its only visible output is the y-axis gutter. Placed outside the
  // scrolling container, it stays in place while the plot above scrolls underneath it,
  // the same effect as a frozen header column in a spreadsheet.
  const axisData = {
    labels,
    datasets: datasets.map((ds) => ({
      ...ds,
      borderColor: "transparent",
      backgroundColor: "transparent",
      borderWidth: 0,
      fill: false,
    })),
  };
  const axisOptions = {
    ...baseLineOptions,
    events: [],
    scales: {
      x: { display: false },
      y: baseLineOptions.scales.y,
    },
    plugins: { legend: { display: false }, tooltip: { enabled: false } },
  };

  // Open scrolled to the recent-history/prediction edge (the same view the fixed
  // version used to show) -- scroll/swipe left from here for older history. Chart.js
  // resizes its canvas asynchronously after mount (via its own ResizeObserver), which
  // can leave a scrollLeft set during the same tick stale; two animation frames
  // reliably wait for that to settle before snapping to the right edge.
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const scrollToEnd = () => {
      el.scrollLeft = el.scrollWidth;
    };
    const raf1 = requestAnimationFrame(() => {
      scrollToEnd();
      requestAnimationFrame(scrollToEnd);
    });
    return () => cancelAnimationFrame(raf1);
  }, [labels.length]);

  const chartWidthPx = labels.length * PX_PER_MONTH;

  return (
    <div className="chart-fixed-row">
      <div className="chart-wrap" style={{ width: AXIS_COLUMN_PX, flex: `0 0 ${AXIS_COLUMN_PX}px` }}>
        <Line data={axisData} options={axisOptions} />
      </div>
      <div className="chart-scroll" ref={scrollRef}>
        <div className="chart-wrap" style={{ width: chartWidthPx, minWidth: "100%" }}>
          <Line data={data} options={plotOptions} />
        </div>
      </div>
    </div>
  );
}
