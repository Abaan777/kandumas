import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import Login from "./Login.jsx";
import { AuthProvider } from "../AuthContext.jsx";
import { login as loginRequest } from "../api/client.js";

vi.mock("../api/client.js", () => ({
  login: vi.fn(),
  register: vi.fn(),
}));

function renderLogin() {
  return render(
    <AuthProvider>
      <MemoryRouter>
        <Login />
      </MemoryRouter>
    </AuthProvider>
  );
}

describe("Login page", () => {
  it("renders a username field, a password field, and links to register/forgot password", () => {
    renderLogin();
    expect(screen.getByPlaceholderText("Enter your username")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Password")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /forgot password/i })).toHaveAttribute("href", "/forgot-password");
    expect(screen.getByRole("link", { name: /create one/i })).toHaveAttribute("href", "/register");
  });

  it("does not expose any demo credentials or hint about where passwords are stored", () => {
    renderLogin();
    expect(screen.queryByText(/\.env/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/demo/i)).not.toBeInTheDocument();
  });

  it("signs in and stores the token/role on successful login", async () => {
    loginRequest.mockResolvedValue({
      data: { access_token: "fake-token", username: "fisherman1", role: "fisherman" },
    });
    const user = userEvent.setup();
    renderLogin();

    await user.type(screen.getByPlaceholderText("Enter your username"), "fisherman1");
    await user.type(screen.getByPlaceholderText("Password"), "Fisherman123!");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(localStorage.getItem("kandumas_token")).toBe("fake-token");
    });
    expect(JSON.parse(localStorage.getItem("kandumas_user"))).toEqual({
      username: "fisherman1",
      role: "fisherman",
    });
  });

  it("shows an error message when login fails", async () => {
    loginRequest.mockRejectedValue({ response: { data: { detail: "Invalid username or password" } } });
    const user = userEvent.setup();
    renderLogin();

    await user.type(screen.getByPlaceholderText("Enter your username"), "fisherman1");
    await user.type(screen.getByPlaceholderText("Password"), "wrong-password");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(await screen.findByText("Invalid username or password")).toBeInTheDocument();
    expect(localStorage.getItem("kandumas_token")).toBeNull();
  });
});
