import { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../AuthContext.jsx";

const NAV_LINKS = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/historical", label: "Historical Data & Trends" },
  { to: "/reports", label: "Reports" },
  { to: "/help", label: "Help" },
];

export default function NavBar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);

  const closeMenu = () => setMenuOpen(false);

  const handleLogout = () => {
    closeMenu();
    logout();
    navigate("/login");
  };

  if (!user) return null;

  const initial = user.username.charAt(0).toUpperCase();

  return (
    <nav className={`navbar ${menuOpen ? "menu-open" : ""}`}>
      <div className="navbar-top-row">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M2 12s3.5-5 10-5 10 5 10 5-3.5 5-10 5-10-5-10-5Z" />
              <circle cx="16.5" cy="10.5" r="0.6" fill="currentColor" stroke="none" />
              <path d="M2 12c-1-1.5-1-2.5 0-4M2 12c-1 1.5-1 2.5 0 4" />
            </svg>
          </span>
          Kandumas
        </div>

        <button
          type="button"
          className="nav-toggle"
          aria-label={menuOpen ? "Close menu" : "Open menu"}
          aria-expanded={menuOpen}
          onClick={() => setMenuOpen((open) => !open)}
        >
          {menuOpen ? (
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          ) : (
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <line x1="3" y1="6" x2="21" y2="6" />
              <line x1="3" y1="12" x2="21" y2="12" />
              <line x1="3" y1="18" x2="21" y2="18" />
            </svg>
          )}
        </button>
      </div>

      <div className="navbar-collapsible">
        <div className="links">
          {NAV_LINKS.map((link) => (
            <NavLink key={link.to} to={link.to} onClick={closeMenu} className={({ isActive }) => (isActive ? "active" : "")}>
              {link.label}
            </NavLink>
          ))}
          {user.role === "admin" && (
            <NavLink to="/admin" onClick={closeMenu} className={({ isActive }) => (isActive ? "active" : "")}>
              Admin
            </NavLink>
          )}
        </div>

        <div className="user-chip">
          <span className="avatar" aria-hidden="true">
            {initial}
          </span>
          <span className="user-meta">
            <span className="username">{user.username}</span>
            <span className="role">{user.role}</span>
          </span>
          <span className="divider" />
          <button onClick={handleLogout}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
              <polyline points="16 17 21 12 16 7" />
              <line x1="21" y1="12" x2="9" y2="12" />
            </svg>
            Logout
          </button>
        </div>
      </div>
    </nav>
  );
}
