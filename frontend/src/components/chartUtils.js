// Shared formatting + option helpers so every chart in the app reads the same way:
// compact numbers, short month labels, no marker clutter on dense series.

export function compactNumber(value) {
  if (value == null) return "-";
  return new Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 1 }).format(value);
}

export function formatMonthLabel(isoDate) {
  const d = new Date(isoDate);
  if (Number.isNaN(d.getTime())) return isoDate;
  return d.toLocaleDateString("en", { month: "short", year: "numeric" });
}

// Keep charts legible: monthly series going back decades are unreadable as one dense
// line, so every chart defaults to the most recent window unless told otherwise.
export function lastNMonths(points, n = 36) {
  return points.slice(-n);
}

export const baseLineOptions = {
  responsive: true,
  maintainAspectRatio: false,
  interaction: { mode: "index", intersect: false },
  elements: {
    point: { radius: 0, hoverRadius: 4, hitRadius: 8 },
    line: { borderWidth: 2 },
  },
  plugins: {
    legend: { display: false },
  },
  scales: {
    x: {
      grid: { display: false },
      ticks: { maxTicksLimit: 7, autoSkip: true, maxRotation: 0 },
    },
    y: {
      grid: { color: "#eef1f0" },
      ticks: { callback: (value) => compactNumber(value) },
    },
  },
};
