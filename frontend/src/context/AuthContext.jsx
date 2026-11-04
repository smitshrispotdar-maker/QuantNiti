import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { api } from "../api.jsx";

const AuthContext = createContext(null);

const TOKEN_KEY = "quantniti_token";
const USER_KEY = "quantniti_user";

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Initialize auth state from localStorage
  useEffect(() => {
    const storedToken = localStorage.getItem(TOKEN_KEY);
    const storedUser = localStorage.getItem(USER_KEY);

    if (storedToken && storedUser) {
      try {
        setToken(storedToken);
        setUser(JSON.parse(storedUser));
      } catch (e) {
        // Invalid stored data, clear it
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
      }
    }
    setIsLoading(false);
  }, []);

  const login = useCallback(async (email, password) => {
    setError(null);
    try {
      const response = await api("/api/auth/login", {
        method: "POST",
        body: { email, password },
      });
      const { access_token, token_type } = response;
      const userResponse = await api("/api/auth/me", {
        headers: { Authorization: `Bearer ${access_token}` },
      });
      setToken(access_token);
      setUser(userResponse);
      localStorage.setItem(TOKEN_KEY, access_token);
      localStorage.setItem(USER_KEY, JSON.stringify(userResponse));
      return { success: true };
    } catch (err) {
      const message = err.detail || err.message || "Login failed";
      setError(message);
      return { success: false, error: message };
    }
  }, []);

  const register = useCallback(async (email, password) => {
    setError(null);
    try {
      const userResponse = await api("/api/auth/register", {
        method: "POST",
        body: { email, password },
      });
      // Auto-login after registration
      const loginResponse = await api("/api/auth/login", {
        method: "POST",
        body: { email, password },
      });
      const { access_token } = loginResponse;
      const meResponse = await api("/api/auth/me", {
        headers: { Authorization: `Bearer ${access_token}` },
      });
      setToken(access_token);
      setUser(meResponse);
      localStorage.setItem(TOKEN_KEY, access_token);
      localStorage.setItem(USER_KEY, JSON.stringify(meResponse));
      return { success: true };
    } catch (err) {
      const message = err.detail || err.message || "Registration failed";
      setError(message);
      return { success: false, error: message };
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await api("/api/auth/logout", { method: "POST" });
    } catch (e) {
      // Ignore logout API errors; we clear local state anyway
    }
    setToken(null);
    setUser(null);
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    setError(null);
  }, []);

  const refreshUser = useCallback(async () => {
    if (!token) return;
    try {
      const userResponse = await api("/api/auth/me");
      setUser(userResponse);
      localStorage.setItem(USER_KEY, JSON.stringify(userResponse));
    } catch (err) {
      // Token likely expired or invalid
      if (err.message?.includes("401") || err.detail?.includes("401") || err.message?.includes("Unauthorized")) {
        logout();
      }
    }
  }, [token, logout]);

  // Attach token to all API requests automatically
  const originalApi = api;
  const authenticatedApi = useCallback(async (path, opts = {}) => {
    const headers = { "Content-Type": "application/json", ...opts.headers };
    if (token && !path.startsWith("/api/auth/login") && !path.startsWith("/api/auth/register")) {
      headers.Authorization = `Bearer ${token}`;
    }
    const res = await fetch(`${import.meta.env.VITE_API_URL || "http://localhost:8000"}${path}`, {
      ...opts,
      headers,
      body: opts.body ? JSON.stringify(opts.body) : undefined,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw Object.assign(new Error("Request failed"), { detail: data.detail || data });
    return data;
  }, [token]);

  // Override the api module's behavior for components using the context
  // Note: Components should import useAuth and use authenticatedApi from context
  // For backward compatibility, we don't modify the original api export

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!token,
        isLoading,
        error,
        login,
        register,
        logout,
        refreshUser,
        authenticatedApi,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}