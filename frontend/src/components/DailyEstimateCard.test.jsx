import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import DailyEstimateCard from "./DailyEstimateCard.jsx";
import { getDailyEstimate } from "../api/client.js";

vi.mock("../api/client.js", () => ({
  getDailyEstimate: vi.fn(),
}));

function todayISO() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function maxDateISO() {
  const d = new Date();
  d.setDate(d.getDate() + 6);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

const SAMPLE_RESPONSE = (date) => ({
  data: {
    region: "North Maldives",
    species: "Skipjack tuna",
    days: [
      {
        date,
        sst: 28.4,
        wind_speed: 5.1,
        baseline_daily_catch_kg: 1000,
        favorability_ratio: 1.2,
        estimated_catch_kg: 1200,
      },
    ],
    disclaimer: "This is not an independently validated daily prediction.",
  },
});

describe("DailyEstimateCard", () => {
  it("defaults the date picker to today, bounded to the next 7 days", async () => {
    getDailyEstimate.mockResolvedValue(SAMPLE_RESPONSE(todayISO()));
    render(<DailyEstimateCard region="North Maldives" species="Skipjack tuna" />);

    const input = screen.getByLabelText(/pick a date/i);
    expect(input).toHaveValue(todayISO());
    expect(input).toHaveAttribute("min", todayISO());
    expect(input).toHaveAttribute("max", maxDateISO());

    await waitFor(() => expect(getDailyEstimate).toHaveBeenCalledWith("North Maldives", "Skipjack tuna", todayISO()));
  });

  it("shows the estimate for the fetched day", async () => {
    getDailyEstimate.mockResolvedValue(SAMPLE_RESPONSE(todayISO()));
    render(<DailyEstimateCard region="North Maldives" species="Skipjack tuna" />);

    expect(await screen.findByText("1,200 kg")).toBeInTheDocument();
    expect(screen.getByText("Today")).toBeInTheDocument();
    expect(screen.getByText("Favorable")).toBeInTheDocument();
  });

  it("refetches when the user picks a different date", async () => {
    getDailyEstimate.mockResolvedValue(SAMPLE_RESPONSE(todayISO()));
    render(<DailyEstimateCard region="North Maldives" species="Skipjack tuna" />);

    await waitFor(() => expect(getDailyEstimate).toHaveBeenLastCalledWith("North Maldives", "Skipjack tuna", todayISO()));

    const target = maxDateISO();
    getDailyEstimate.mockResolvedValue(SAMPLE_RESPONSE(target));
    const input = screen.getByLabelText(/pick a date/i);
    fireEvent.change(input, { target: { value: target } });

    await waitFor(() => expect(getDailyEstimate).toHaveBeenLastCalledWith("North Maldives", "Skipjack tuna", target));
  });

  it("shows an error message when the request fails", async () => {
    getDailyEstimate.mockRejectedValue({ response: { data: { detail: "Date must be between ... and ..." } } });
    render(<DailyEstimateCard region="North Maldives" species="Skipjack tuna" />);

    expect(await screen.findByText(/date must be between/i)).toBeInTheDocument();
  });
});
