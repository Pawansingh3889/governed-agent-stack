"use client";

import { useCallback, useEffect, useState } from "react";

export function useAuth() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Check for existing token
    if (typeof window !== "undefined") {
      const token = localStorage.getItem("fm_token");
      setIsAuthenticated(!!token);
    }
    setIsLoading(false);
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const { login: apiLogin } = await import("@/lib/api");
    await apiLogin(username, password);
    setIsAuthenticated(true);
  }, []);

  const logout = useCallback(() => {
    const { clearToken } = require("@/lib/api");
    clearToken();
    setIsAuthenticated(false);
  }, []);

  return { isAuthenticated, isLoading, login, logout };
}
