import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../AuthContext.jsx";
import PasswordField from "../components/PasswordField.jsx";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(username, password);
      navigate("/dashboard");
    } catch (err) {
      setError(err.response?.data?.detail || "Invalid username or password");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-shell">
      <form className="login-card" onSubmit={handleSubmit}>
        <h1>Kandumas</h1>
        <p className="subtitle">Sign in to view Maldives tuna catch forecasts, historical trends and reports.</p>

        <label htmlFor="username" style={{ display: "block", marginBottom: "0.3rem", fontSize: "0.85rem", color: "#6b7c7e" }}>
          Username
        </label>
        <input
          id="username"
          type="text"
          autoComplete="username"
          placeholder="Enter your username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          required
        />

        <label htmlFor="password" style={{ display: "block", marginBottom: "0.3rem", fontSize: "0.85rem", color: "#6b7c7e" }}>
          Password
        </label>
        <PasswordField
          id="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />

        <div className="auth-links">
          <span />
          <Link to="/forgot-password">Forgot password?</Link>
        </div>

        {error && <p className="error-text">{error}</p>}

        <button className="btn-primary" type="submit" disabled={loading}>
          {loading ? "Signing in..." : "Sign in"}
        </button>

        <p className="auth-footer">
          Don&apos;t have an account? <Link to="/register">Create one</Link>
        </p>
      </form>
    </div>
  );
}
