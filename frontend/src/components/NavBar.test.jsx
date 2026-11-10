import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import NavBar from "./NavBar.jsx";
import { AuthProvider } from "../AuthContext.jsx";

function renderNavBar(userOverrides) {
  if (userOverrides) {
    localStorage.setItem("kandumas_user", JSON.stringify(userOverrides));
  }
  return render(
    <AuthProvider>
      <MemoryRouter>
        <NavBar />
      </MemoryRouter>
    </AuthProvider>
  );
}

describe("NavBar", () => {
  it("renders nothing when no user is signed in", () => {
    const { container } = renderNavBar();
    expect(container).toBeEmptyDOMElement();
  });

  it("hides the Admin link for non-admin roles", () => {
    renderNavBar({ username: "fisherman1", role: "fisherman" });
    expect(screen.queryByRole("link", { name: "Admin" })).not.toBeInTheDocument();
  });

  it("shows the Admin link for admin users", () => {
    renderNavBar({ username: "admin1", role: "admin" });
    expect(screen.getByRole("link", { name: "Admin" })).toBeInTheDocument();
  });

  it("starts with the mobile menu collapsed, and the toggle opens/closes it", async () => {
    const user = userEvent.setup();
    renderNavBar({ username: "fisherman1", role: "fisherman" });

    const nav = screen.getByRole("navigation");
    expect(nav).not.toHaveClass("menu-open");

    await user.click(screen.getByRole("button", { name: /open menu/i }));
    expect(nav).toHaveClass("menu-open");

    await user.click(screen.getByRole("button", { name: /close menu/i }));
    expect(nav).not.toHaveClass("menu-open");
  });

  it("closes the mobile menu after clicking a nav link", async () => {
    const user = userEvent.setup();
    renderNavBar({ username: "fisherman1", role: "fisherman" });

    await user.click(screen.getByRole("button", { name: /open menu/i }));
    expect(screen.getByRole("navigation")).toHaveClass("menu-open");

    await user.click(screen.getByRole("link", { name: "Reports" }));
    expect(screen.getByRole("navigation")).not.toHaveClass("menu-open");
  });
});
