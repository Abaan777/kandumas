import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import ForgotPassword from "./ForgotPassword.jsx";
import { forgotPassword } from "../api/client.js";

vi.mock("../api/client.js", () => ({
  forgotPassword: vi.fn(),
}));

function renderForgotPassword() {
  return render(
    <MemoryRouter>
      <ForgotPassword />
    </MemoryRouter>
  );
}

describe("ForgotPassword page", () => {
  it("shows the generated reset link after submitting a username", async () => {
    forgotPassword.mockResolvedValue({
      data: {
        detail: "If an account exists for that username, a password reset link has been generated.",
        reset_token: "abc123",
        reset_url: "http://localhost:5173/reset-password?token=abc123",
      },
    });
    const user = userEvent.setup();
    renderForgotPassword();

    await user.type(screen.getByPlaceholderText("Enter your username"), "fisherman1");
    await user.click(screen.getByRole("button", { name: /send reset link/i }));

    await waitFor(() => {
      expect(screen.getByText("http://localhost:5173/reset-password?token=abc123")).toBeInTheDocument();
    });
    expect(forgotPassword).toHaveBeenCalledWith("fisherman1");
  });

  it("shows the generic confirmation even without a reset_url (unknown username case)", async () => {
    forgotPassword.mockResolvedValue({
      data: {
        detail: "If an account exists for that username, a password reset link has been generated.",
        reset_token: null,
        reset_url: null,
      },
    });
    const user = userEvent.setup();
    renderForgotPassword();

    await user.type(screen.getByPlaceholderText("Enter your username"), "nobody-here");
    await user.click(screen.getByRole("button", { name: /send reset link/i }));

    expect(
      await screen.findByText(/a password reset link has been generated/i)
    ).toBeInTheDocument();
    // No link box should render when the backend didn't return one.
    expect(screen.queryByRole("button", { name: /copy/i })).not.toBeInTheDocument();
  });
});
