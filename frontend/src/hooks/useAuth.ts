"use client";

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import type { User, LoginCredentials, RegisterData } from "@/types";

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const checkAuth = useCallback(async () => {
    const token = api.getToken();
    if (!token) {
      setLoading(false);
      return;
    }

    try {
      const currentUser = await api.getCurrentUser();
      setUser(currentUser);
    } catch {
      api.logout();
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  const login = async (credentials: LoginCredentials) => {
    setError(null);
    try {
      await api.login(credentials);
      const currentUser = await api.getCurrentUser();
      setUser(currentUser);
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
      return false;
    }
  };

  const register = async (data: RegisterData) => {
    setError(null);
    try {
      await api.register(data);
      // Auto-login after registration
      return login({ username: data.email, password: data.password });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
      return false;
    }
  };

  const logout = () => {
    api.logout();
    setUser(null);
  };

  return {
    user,
    loading,
    error,
    login,
    register,
    logout,
    isAuthenticated: !!user,
  };
}
