import { useState } from "react";

// Hold the eye icon to reveal the password while pressed; release (or move the
// pointer away, or lift a finger) to hide it again. Works with mouse and touch, and
// with keyboard (space/enter) for accessibility.
export default function PasswordField({ id, value, onChange, placeholder = "Password", required }) {
  const [revealed, setRevealed] = useState(false);

  const show = () => setRevealed(true);
  const hide = () => setRevealed(false);

  return (
    <div className="password-field">
      <input
        id={id}
        type={revealed ? "text" : "password"}
        placeholder={placeholder}
        value={value}
        onChange={onChange}
        required={required}
        autoComplete="current-password"
      />
      <button
        type="button"
        className="password-toggle"
        aria-label="Hold to show password"
        title="Hold to show password"
        tabIndex={-1}
        onMouseDown={show}
        onMouseUp={hide}
        onMouseLeave={hide}
        onTouchStart={(e) => {
          e.preventDefault();
          show();
        }}
        onTouchEnd={hide}
        onTouchCancel={hide}
        onKeyDown={(e) => {
          if (e.key === " " || e.key === "Enter") show();
        }}
        onKeyUp={(e) => {
          if (e.key === " " || e.key === "Enter") hide();
        }}
        onBlur={hide}
      >
        {revealed ? (
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M17.94 17.94A10.94 10.94 0 0 1 12 20c-7 0-11-8-11-8a18.5 18.5 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
            <line x1="1" y1="1" x2="23" y2="23" />
          </svg>
        ) : (
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8Z" />
            <circle cx="12" cy="12" r="3" />
          </svg>
        )}
      </button>
    </div>
  );
}
