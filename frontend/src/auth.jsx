import { createContext, useContext, useEffect, useState } from "react";
import { api } from "./api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  async function refresh() {
    const token = localStorage.getItem("hs_token");
    if (!token) {
      setUser(null);
      setLoading(false);
      return null;
    }
    try {
      const me = await api.get("/api/auth/me");
      setUser(me);
      return me;
    } catch {
      localStorage.removeItem("hs_token");
      setUser(null);
      return null;
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function login(email, password) {
    const data = await api.post("/api/auth/login", { email, password });
    localStorage.setItem("hs_token", data.token);
    setUser(data.user);
    return data.user;
  }

  async function register(payload) {
    const data = await api.post("/api/auth/register", payload);
    localStorage.setItem("hs_token", data.token);
    setUser(data.user);
    return data.user;
  }

  async function logout() {
    try {
      await api.post("/api/auth/logout");
    } catch {
      /* token may already be expired */
    }
    localStorage.removeItem("hs_token");
    setUser(null);
  }

  return <AuthContext.Provider value={{ user, loading, login, register, logout, refresh }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}
