import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import ResetPassword from "./ResetPassword.jsx";
import { resetPassword } from "../api/client.js";

vi.mock("../api/client.js", () => ({
  resetPassword: vi.fn(),
}));

function renderAt(path) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <ResetPassword />
    </MemoryRouter>
  );
}

describe("ResetPassword page", () => {
  it("prompts for a new link when no token is present in the URL", () => {
    renderAt("/reset-password");
    expect(screen.getByText(/needs a valid reset link/i)).toBeInTheDocument();
  });

  it("rejects mismatched passwords without calling the API", async () => {
    const user = userEvent.setup();
    renderAt("/reset-password?token=abc123");

    await user.type(screen.getByPlaceholderText("At least 8 characters"), "NewStrongPass1!");
    await user.type(screen.getByPlaceholderText("Re-enter your new password"), "Different1!");
    await user.click(screen.getByRole("button", { name: /update password/i }));

    expect(await screen.findByText("Passwords do not match.")).toBeInTheDocument();
    expect(resetPassword).not.toHaveBeenCalled();
  });

  it("submits the token and new password, and shows a success message", async () => {
    resetPassword.mockResolvedValue({ data: { detail: "Your password has been updated." } });
    const user = userEvent.setup();
    renderAt("/reset-password?token=abc123");

    await user.type(screen.getByPlaceholderText("At least 8 characters"), "NewStrongPass1!");
    await user.type(screen.getByPlaceholderText("Re-enter your new password"), "NewStrongPass1!");
    await user.click(screen.getByRole("button", { name: /update password/i }));

    await waitFor(() => {
      expect(resetPassword).toHaveBeenCalledWith("abc123", "NewStrongPass1!");
    });
    expect(await screen.findByText(/password has been updated/i)).toBeInTheDocument();
  });

  it("shows the server's error message when the token is invalid or expired", async () => {
    resetPassword.mockRejectedValue({ response: { data: { detail: "This reset link is invalid or has expired." } } });
    const user = userEvent.setup();
    renderAt("/reset-password?token=expired-token");

    await user.type(screen.getByPlaceholderText("At least 8 characters"), "NewStrongPass1!");
    await user.type(screen.getByPlaceholderText("Re-enter your new password"), "NewStrongPass1!");
    await user.click(screen.getByRole("button", { name: /update password/i }));

    expect(await screen.findByText("This reset link is invalid or has expired.")).toBeInTheDocument();
  });
});
