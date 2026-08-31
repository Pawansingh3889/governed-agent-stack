"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getDashboardStats } from "@/lib/api";
import { Sidebar } from "@/components/Sidebar";
import { KPICard } from "@/components/KPICard";

export default function DashboardPage() {
  const [stats, setStats] = useState<{
    production_runs_7d: number;
    waste_kg_7d: number;
    waste_cost_7d: number;
    pending_orders: number;
  } | null>(null);
  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem("fm_token");
    if (!token) {
      router.push("/");
      return;
    }
    getDashboardStats().then(setStats).catch(console.error);
  }, [router]);

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-6 pb-20 md:pb-6">
        <h1 className="text-2xl font-bold mb-6">📊 Factory Dashboard</h1>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
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

        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-lg font-semibold mb-4">Quick Start</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <a
              href="/chat"
              className="p-4 rounded-lg border border-gray-200 hover:border-brand-500 hover:shadow transition-all"
            >
              <span className="text-2xl">💬</span>
              <h3 className="font-medium mt-2">Ask a Question</h3>
              <p className="text-sm text-gray-500 mt-1">
                Query production, waste, orders in plain English
              </p>
            </a>
            <a
              href="/compliance"
              className="p-4 rounded-lg border border-gray-200 hover:border-brand-500 hover:shadow transition-all"
            >
              <span className="text-2xl">📋</span>
              <h3 className="font-medium mt-2">Compliance</h3>
              <p className="text-sm text-gray-500 mt-1">
                Temperature, allergens, batch traceability
              </p>
            </a>
            <a
              href="/waste"
              className="p-4 rounded-lg border border-gray-200 hover:border-brand-500 hover:shadow transition-all"
            >
              <span className="text-2xl">📈</span>
              <h3 className="font-medium mt-2">Yield & Waste</h3>
              <p className="text-sm text-gray-500 mt-1">
                Trends, predictions, AI analysis
              </p>
            </a>
          </div>
        </div>
      </main>
    </div>
  );
}
