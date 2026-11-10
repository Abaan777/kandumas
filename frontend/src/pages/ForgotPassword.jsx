import { useState } from "react";
import { Link } from "react-router-dom";
import { forgotPassword } from "../api/client.js";

export default function ForgotPassword() {
  const [username, setUsername] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [resetUrl, setResetUrl] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const { data } = await forgotPassword(username);
      setSubmitted(true);
      setResetUrl(data.reset_url || null);
    } catch (err) {
      setError(err.response?.data?.detail || "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(resetUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard access can fail (e.g. insecure context) -- the link is still
      // selectable/copyable by hand from the box below, so this is non-fatal.
    }
  };

  return (
    <div className="login-shell">
      <div className="login-card">
        <h1>Reset your password</h1>
        <p className="subtitle">Enter your username and we'll generate a password reset link.</p>

        {!submitted ? (
          <form onSubmit={handleSubmit}>
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

            {error && <p className="error-text">{error}</p>}

            <button className="btn-primary" type="submit" disabled={loading}>
              {loading ? "Generating link..." : "Send reset link"}
            </button>
          </form>
        ) : (
          <>
            <p className="success-text">
              If an account exists for that username, a password reset link has been generated below.
            </p>
            {resetUrl && (
              <>
                <div className="reset-link-box">
                  <code>{resetUrl}</code>
                  <button type="button" className="btn-secondary" onClick={handleCopy}>
                    {copied ? "Copied" : "Copy"}
                  </button>
                </div>
                <p className="helper-text">
                  Email delivery isn't configured yet, so the link is shown here directly instead of
                  being emailed. It expires in 30 minutes and can only be used once.
                </p>
                <Link to={resetUrl.replace(window.location.origin, "")}>
                  <button type="button" className="btn-primary" style={{ marginTop: "0.5rem" }}>
                    Continue to reset password
                  </button>
                </Link>
              </>
            )}
          </>
        )}

        <p className="auth-footer">
          Remembered your password? <Link to="/login">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
