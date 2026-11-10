import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import PasswordField from "../components/PasswordField.jsx";
import { resetPassword } from "../api/client.js";

export default function ResetPassword() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") || "";
  const navigate = useNavigate();

  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (newPassword !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    if (newPassword.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }

    setLoading(true);
    try {
      await resetPassword(token, newPassword);
      setSuccess(true);
      setTimeout(() => navigate("/login"), 2500);
    } catch (err) {
      setError(err.response?.data?.detail || "This reset link is invalid or has expired.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-shell">
      <div className="login-card">
        <h1>Set a new password</h1>

        {!token ? (
          <>
            <p className="error-text">
              This page needs a valid reset link. Please request a new one.
            </p>
            <Link to="/forgot-password">
              <button type="button" className="btn-primary">
                Request a reset link
              </button>
            </Link>
          </>
        ) : success ? (
          <p className="success-text">Your password has been updated. Redirecting to sign in...</p>
        ) : (
          <form onSubmit={handleSubmit}>
            <p className="subtitle">Choose a new password for your account.</p>

            <label htmlFor="new-password" style={{ display: "block", marginBottom: "0.3rem", fontSize: "0.85rem", color: "#6b7c7e" }}>
              New password
            </label>
            <PasswordField
              id="new-password"
              placeholder="At least 8 characters"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
            />

            <label htmlFor="confirm-new-password" style={{ display: "block", marginBottom: "0.3rem", fontSize: "0.85rem", color: "#6b7c7e" }}>
              Confirm new password
            </label>
            <PasswordField
              id="confirm-new-password"
              placeholder="Re-enter your new password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
            />

            {error && <p className="error-text">{error}</p>}

            <button className="btn-primary" type="submit" disabled={loading}>
              {loading ? "Updating..." : "Update password"}
            </button>
          </form>
        )}

        <p className="auth-footer">
          <Link to="/login">Back to sign in</Link>
        </p>
      </div>
    </div>
  );
}
