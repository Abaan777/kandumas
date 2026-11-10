import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import ProtectedRoute from "./ProtectedRoute.jsx";
import { AuthProvider } from "../AuthContext.jsx";

function renderAt(path, roles) {
  return render(
    <AuthProvider>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/login" element={<div>Login page</div>} />
          <Route path="/dashboard" element={<div>Dashboard page</div>} />
          <Route
            path="/admin"
            element={
              <ProtectedRoute roles={roles}>
                <div>Admin page</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>
    </AuthProvider>
  );
}

describe("ProtectedRoute", () => {
  it("redirects to /login when no user is signed in", () => {
    renderAt("/admin", ["admin"]);
    expect(screen.getByText("Login page")).toBeInTheDocument();
  });

  it("redirects to /dashboard when the signed-in user's role isn't allowed", () => {
    localStorage.setItem("kandumas_user", JSON.stringify({ username: "fisherman1", role: "fisherman" }));
    renderAt("/admin", ["admin"]);
    expect(screen.getByText("Dashboard page")).toBeInTheDocument();
  });

  it("renders the protected content when the signed-in user's role is allowed", () => {
    localStorage.setItem("kandumas_user", JSON.stringify({ username: "admin1", role: "admin" }));
    renderAt("/admin", ["admin"]);
    expect(screen.getByText("Admin page")).toBeInTheDocument();
  });

  it("renders the protected content for any authenticated user when no roles are specified", () => {
    localStorage.setItem("kandumas_user", JSON.stringify({ username: "officer1", role: "officer" }));
    renderAt("/admin", undefined);
    expect(screen.getByText("Admin page")).toBeInTheDocument();
  });
});
