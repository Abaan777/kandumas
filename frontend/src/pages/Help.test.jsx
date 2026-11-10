import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import Help from "./Help.jsx";

describe("Help page", () => {
  it("renders guidance on reading RMSE/MAPE and the region map colors", () => {
    render(<Help />);
    expect(screen.getByText(/What do RMSE and MAPE mean/i)).toBeInTheDocument();
    expect(screen.getByText(/what do the colors mean/i)).toBeInTheDocument();
  });
});
