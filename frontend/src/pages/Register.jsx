import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../AuthContext.jsx";
import PasswordField from "../components/PasswordField.jsx";

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }

    setLoading(true);
    try {
      await register(username, password);
      navigate("/dashboard");
    } catch (err) {
      setError(err.response?.data?.detail || "Could not create that account.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-shell">
      <form className="login-card" onSubmit={handleSubmit}>
        <h1>Create your account</h1>
        <p className="subtitle">
          New accounts are registered with the Fisherman role. Fisheries Officer and
          Administrator access is granted separately.
        </p>

        <label htmlFor="username" style={{ display: "block", marginBottom: "0.3rem", fontSize: "0.85rem", color: "#6b7c7e" }}>
          Username
        </label>
        <input
          id="username"
          type="text"
          autoComplete="username"
          placeholder="Choose a username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          minLength={3}
          required
        />

        <label htmlFor="password" style={{ display: "block", marginBottom: "0.3rem", fontSize: "0.85rem", color: "#6b7c7e" }}>
          Password
        </label>
        <PasswordField
          id="password"
          placeholder="At least 8 characters"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />

        <label htmlFor="confirm-password" style={{ display: "block", marginBottom: "0.3rem", fontSize: "0.85rem", color: "#6b7c7e" }}>
          Confirm password
        </label>
        <PasswordField
          id="confirm-password"
          placeholder="Re-enter your password"
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          required
        />

        {error && <p className="error-text">{error}</p>}

        <button className="btn-primary" type="submit" disabled={loading}>
          {loading ? "Creating account..." : "Create account"}
        </button>

        <p className="auth-footer">
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </form>
    </div>
  );
}
