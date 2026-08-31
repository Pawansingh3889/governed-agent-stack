"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  getAllergens,
  getComplianceScores,
  getTemperatureExcursions,
  traceBatch,
} from "@/lib/floor";
import { useAuth } from "@/hooks/useAuth";
import { DataTable } from "@/components/DataTable";

export default function CompliancePage() {
  const [scores, setScores] = useState<Record<string, number> | null>(null);
  const [batchCode, setBatchCode] = useState("");
  const [trace, setTrace] = useState<{
    raw_materials: Record<string, unknown>[];
    production: Record<string, unknown>[];
    orders: Record<string, unknown>[];
  } | null>(null);
  const [allergens, setAllergens] = useState<Record<string, unknown>[]>([]);
  const [excursions, setExcursions] = useState<Record<string, unknown>[]>([]);
  const { gate } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (gate === "login") {
      router.push("/login");
      return;
    }
    if (gate !== "ok") return;
    getComplianceScores().then((d) => setScores(d.scores)).catch(console.error);
    getAllergens().then(setAllergens).catch(console.error);
    getTemperatureExcursions(7).then(setExcursions).catch(console.error);
  }, [gate, router]);

  const handleTrace = async (e: FormEvent) => {
    e.preventDefault();
    if (!batchCode.trim()) return;
    const result = await traceBatch(batchCode);
    setTrace(result);
  };

  if (gate !== "ok") return null;

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-semibold text-white">Compliance & Audit</h1>
        <p className="mt-1 text-sm text-zinc-500">
          Scores, batch traceability, temperature and allergen data from FloorMind
        </p>
      </header>

      {scores && (
        <div className="grid grid-cols-3 gap-4">
          {Object.entries(scores).map(([key, val]) => (
            <div
              key={key}
              className={`rounded-xl border p-4 text-center ${
                val >= 95
                  ? "border-green-500/30 bg-green-500/10"
                  : val >= 85
                    ? "border-yellow-500/30 bg-yellow-500/10"
                    : "border-red-500/30 bg-red-500/10"
              }`}
            >
              <p className="text-sm text-zinc-400">{key}</p>
              <p className="mt-1 text-3xl font-bold text-white">{val}%</p>
            </div>
          ))}
        </div>
      )}

      <section className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-6">
        <h2 className="mb-4 text-lg font-semibold text-white">Batch Traceability</h2>
        <form onSubmit={handleTrace} className="mb-4 flex gap-2">
          <input
            type="text"
            value={batchCode}
            onChange={(e) => setBatchCode(e.target.value)}
            placeholder="e.g. PR-260329-1"
            className="flex-1 rounded-lg border border-zinc-700 bg-zinc-950 px-4 py-2 text-sm text-zinc-200 placeholder-zinc-500 focus:border-transparent focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
          <button
            type="submit"
            className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-600"
          >
            Trace
          </button>
        </form>
        {trace && (
          <div className="space-y-4">
            {trace.raw_materials.length > 0 && (
              <div>
                <h3 className="mb-2 font-medium text-zinc-300">Raw Materials</h3>
                <DataTable data={trace.raw_materials} />
              </div>
            )}
            {trace.production.length > 0 && (
              <div>
                <h3 className="mb-2 font-medium text-zinc-300">Production</h3>
                <DataTable data={trace.production} />
              </div>
            )}
            {trace.orders.length > 0 && (
              <div>
                <h3 className="mb-2 font-medium text-zinc-300">Orders</h3>
                <DataTable data={trace.orders} />
              </div>
            )}
          </div>
        )}
      </section>

      <section className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-6">
        <h2 className="mb-4 text-lg font-semibold text-white">Temperature Excursions (7d)</h2>
        {excursions.length > 0 ? (
          <DataTable data={excursions} />
        ) : (
          <p className="text-green-400">No temperature excursions in the last 7 days</p>
        )}
      </section>

      <section className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-6">
        <h2 className="mb-4 text-lg font-semibold text-white">Allergen Matrix</h2>
        <DataTable data={allergens} />
      </section>
    </div>
  );
}