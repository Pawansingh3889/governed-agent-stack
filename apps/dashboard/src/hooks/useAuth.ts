"use client";

import { useEffect, useState } from "react";
import { isDevMode } from "@/lib/floor";

export function useAuth() {
  const [gate, setGate] = useState<"loading" | "ok" | "login">("loading");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const token = localStorage.getItem("fm_token");
      if (token) {
        if (!cancelled) setGate("ok");
        return;
      }
      const dev = await isDevMode();
      if (cancelled) return;
      setGate(dev ? "ok" : "login");
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return { gate };
}