import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Filler } from "chart.js";
import { Line } from "react-chartjs-2";
import { baseLineOptions, compactNumber, formatMonthLabel, lastNMonths } from "./chartUtils.js";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Filler);

const WINDOW_MONTHS = 36;

export default function HistoricalChart({ points = [], variable = "catch_kg", label = "Catch (kg)", color = "#1f6f8b", unit = "" }) {
  const recent = lastNMonths(points, WINDOW_MONTHS);

  const data = {
    labels: recent.map((p) => formatMonthLabel(p.month)),
    datasets: [
      {
        label,
        data: recent.map((p) => p[variable]),
        borderColor: color,
        backgroundColor: `${color}22`,
        tension: 0.3,
        spanGaps: true,
        fill: true,
      },
    ],
  };

  const options = {
    ...baseLineOptions,
    plugins: {
      ...baseLineOptions.plugins,
      tooltip: {
        callbacks: {
          label: (ctx) => `${label}: ${compactNumber(ctx.parsed.y)}${unit}`,
        },
      },
    },
  };

  // The underlying source datasets don't all cover the same date range (see
  // docs/DATA_SOURCES.md -- e.g. the wind speed dataset's real coverage ends well
  // before SST's). When that means this variable's line stops short of the window's
  // most recent month, say so explicitly instead of letting it just trail off, which
  // otherwise reads as a rendering bug rather than a real, documented data gap.
  const lastRealPoint = [...recent].reverse().find((p) => p[variable] != null);
  const windowEnd = recent[recent.length - 1];
  const hasNoData = recent.length > 0 && !lastRealPoint;
  const hasTrailingGap = lastRealPoint && windowEnd && lastRealPoint.month !== windowEnd.month;

  return (
    <div className="chart-wrap">
      <Line data={data} options={options} />
      {hasNoData && (
        <p className="helper-text" style={{ marginTop: "0.5rem" }}>
          No {label.toLowerCase()} data available for this period.
        </p>
      )}
      {hasTrailingGap && (
        <p className="helper-text" style={{ marginTop: "0.5rem" }}>
          {label} data available through {formatMonthLabel(lastRealPoint.month)} -- the source dataset's
          coverage doesn't extend further yet (see docs/DATA_SOURCES.md).
        </p>
      )}
    </div>
  );
}
