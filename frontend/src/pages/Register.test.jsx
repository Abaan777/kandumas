import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import Register from "./Register.jsx";
import { AuthProvider } from "../AuthContext.jsx";
import { register as registerRequest } from "../api/client.js";

vi.mock("../api/client.js", () => ({
  login: vi.fn(),
  register: vi.fn(),
}));

function renderRegister() {
  return render(
    <AuthProvider>
      <MemoryRouter>
        <Register />
      </MemoryRouter>
    </AuthProvider>
  );
}

describe("Register page", () => {
  it("tells the user new accounts are created with the Fisherman role", () => {
    renderRegister();
    expect(screen.getByText(/registered with the Fisherman role/i)).toBeInTheDocument();
  });

  it("rejects mismatched passwords without calling the API", async () => {
    const user = userEvent.setup();
    renderRegister();

    await user.type(screen.getByPlaceholderText("Choose a username"), "newuser1");
    await user.type(screen.getByPlaceholderText("At least 8 characters"), "StrongPass1!");
    await user.type(screen.getByPlaceholderText("Re-enter your password"), "Different1!");
    await user.click(screen.getByRole("button", { name: /create account/i }));

    expect(await screen.findByText("Passwords do not match.")).toBeInTheDocument();
    expect(registerRequest).not.toHaveBeenCalled();
  });

  it("rejects a password shorter than 8 characters without calling the API", async () => {
    const user = userEvent.setup();
    renderRegister();

    await user.type(screen.getByPlaceholderText("Choose a username"), "newuser1");
    await user.type(screen.getByPlaceholderText("At least 8 characters"), "short1");
    await user.type(screen.getByPlaceholderText("Re-enter your password"), "short1");
    await user.click(screen.getByRole("button", { name: /create account/i }));

    expect(await screen.findByText(/at least 8 characters/i)).toBeInTheDocument();
    expect(registerRequest).not.toHaveBeenCalled();
  });

  it("registers and stores the session on success", async () => {
    registerRequest.mockResolvedValue({
      data: { access_token: "fake-token", username: "newuser1", role: "fisherman" },
    });
    const user = userEvent.setup();
    renderRegister();

    await user.type(screen.getByPlaceholderText("Choose a username"), "newuser1");
    await user.type(screen.getByPlaceholderText("At least 8 characters"), "StrongPass1!");
    await user.type(screen.getByPlaceholderText("Re-enter your password"), "StrongPass1!");
    await user.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => {
      expect(localStorage.getItem("kandumas_token")).toBe("fake-token");
    });
    expect(registerRequest).toHaveBeenCalledWith("newuser1", "StrongPass1!");
  });

  it("shows the server's error message (e.g. username already taken)", async () => {
    registerRequest.mockRejectedValue({ response: { data: { detail: "That username is already taken." } } });
    const user = userEvent.setup();
    renderRegister();

    await user.type(screen.getByPlaceholderText("Choose a username"), "fisherman1");
    await user.type(screen.getByPlaceholderText("At least 8 characters"), "StrongPass1!");
    await user.type(screen.getByPlaceholderText("Re-enter your password"), "StrongPass1!");
    await user.click(screen.getByRole("button", { name: /create account/i }));

    expect(await screen.findByText("That username is already taken.")).toBeInTheDocument();
  });
});
