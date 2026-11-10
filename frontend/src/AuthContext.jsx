import { createContext, useContext, useState } from "react";
import { login as loginRequest, register as registerRequest } from "./api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const raw = localStorage.getItem("kandumas_user");
    return raw ? JSON.parse(raw) : null;
  });

  const _applySession = (data) => {
    localStorage.setItem("kandumas_token", data.access_token);
    localStorage.setItem("kandumas_user", JSON.stringify({ username: data.username, role: data.role }));
    setUser({ username: data.username, role: data.role });
    return data;
  };

  const login = async (username, password) => _applySession((await loginRequest(username, password)).data);

  // Self-registration always creates a Fisherman account and signs the new user in
  // immediately (the backend returns the same shape as /auth/login).
  const register = async (username, password) => _applySession((await registerRequest(username, password)).data);

  const logout = () => {
    localStorage.removeItem("kandumas_token");
    localStorage.removeItem("kandumas_user");
    setUser(null);
  };

  return <AuthContext.Provider value={{ user, login, register, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
