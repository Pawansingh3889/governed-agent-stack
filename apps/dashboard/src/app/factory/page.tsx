"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getDashboardStats, getAlerts } from "@/lib/floor";
import { useAuth } from "@/hooks/useAuth";
import { KPICard } from "@/components/KPICard";
import { AlertCard } from "@/components/AlertCard";

export default function FactoryPage() {
  const [stats, setStats] = useState<{
    production_runs_7d: number;
    waste_kg_7d: number;
    waste_cost_7d: number;
    pending_orders: number;
  } | null>(null);
  const [alerts, setAlerts] = useState<
    { level: string; title: string; message: string; category: string }[]
  >([]);
  const { gate } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (gate === "login") {
      router.push("/login");
      return;
    }
    if (gate !== "ok") return;
    getDashboardStats().then(setStats).catch(console.error);
    getAlerts().then(setAlerts).catch(console.error);
  }, [gate, router]);

  if (gate !== "ok") return null;

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-semibold text-white">Factory Dashboard</h1>
        <p className="mt-1 text-sm text-zinc-500">
          Production, waste, orders and alerts from FloorMind
        </p>
      </header>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <KPICard
          label="Production Runs (7d)"
          value={stats?.production_runs_7d ?? "—"}
        />
        <KPICard
          label="Waste (7d)"
          value={stats ? `${stats.waste_kg_7d.toLocaleString()} kg` : "—"}
        />
        <KPICard
          label="Waste Cost (7d)"
          value={stats ? `£${stats.waste_cost_7d.toLocaleString()}` : "—"}
          color="danger"
        />
        <KPICard
          label="Pending Orders"
          value={stats?.pending_orders ?? "—"}
        />
      </div>

      <section>
        <h2 className="mb-3 text-sm font-medium text-zinc-400">Active Alerts</h2>
        {alerts.length === 0 ? (
          <p className="text-sm text-zinc-500">No active alerts.</p>
        ) : (
          <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
            {alerts.map((a, i) => (
              <AlertCard
                key={i}
                level={a.level as "critical" | "warning" | "info"}
                title={a.title}
                message={a.message}
                category={a.category}
              />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}