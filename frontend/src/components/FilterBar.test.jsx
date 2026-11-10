import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import FilterBar from "./FilterBar.jsx";
import { getRegions, getSpecies } from "../api/client.js";

vi.mock("../api/client.js", () => ({
  getRegions: vi.fn(),
  getSpecies: vi.fn(),
}));

const REGIONS = [
  { id: 1, name: "North Maldives" },
  { id: 2, name: "South Maldives" },
];
const SPECIES = [
  { id: 1, name: "Skipjack tuna" },
  { id: 2, name: "Yellowfin tuna" },
];

describe("FilterBar", () => {
  it("loads regions and species from the API and renders them as options", async () => {
    getRegions.mockResolvedValue({ data: REGIONS });
    getSpecies.mockResolvedValue({ data: SPECIES });

    render(<FilterBar value={{}} onChange={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByRole("option", { name: "North Maldives" })).toBeInTheDocument();
    });
    expect(screen.getByRole("option", { name: "South Maldives" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Skipjack tuna" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Yellowfin tuna" })).toBeInTheDocument();
  });

  it("calls onChange with the merged filter value when a selection changes", async () => {
    getRegions.mockResolvedValue({ data: REGIONS });
    getSpecies.mockResolvedValue({ data: SPECIES });
    const onChange = vi.fn();
    const user = userEvent.setup();

    render(<FilterBar value={{ species: "Skipjack tuna" }} onChange={onChange} />);

    await waitFor(() => screen.getByRole("option", { name: "North Maldives" }));
    await user.selectOptions(screen.getByLabelText("Region"), "North Maldives");

    expect(onChange).toHaveBeenCalledWith({ species: "Skipjack tuna", region: "North Maldives" });
  });
});
