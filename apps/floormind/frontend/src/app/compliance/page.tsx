"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  getAllergens,
  getComplianceScores,
  getTemperatureExcursions,
  traceBatch,
} from "@/lib/api";
import { Sidebar } from "@/components/Sidebar";
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
  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem("fm_token");
    if (!token) { router.push("/"); return; }
    getComplianceScores().then((d) => setScores(d.scores)).catch(console.error);
    getAllergens().then(setAllergens).catch(console.error);
    getTemperatureExcursions(7).then(setExcursions).catch(console.error);
  }, [router]);

  const handleTrace = async (e: FormEvent) => {
    e.preventDefault();
    if (!batchCode.trim()) return;
    const result = await traceBatch(batchCode);
    setTrace(result);
  };

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-6 pb-20 md:pb-6 max-w-6xl">
        <h1 className="text-2xl font-bold mb-6">📋 Compliance & Audit</h1>

        {/* Scores */}
        {scores && (
          <div className="grid grid-cols-3 gap-4 mb-8">
            {Object.entries(scores).map(([key, val]) => (
              <div
                key={key}
                className={`rounded-xl border p-4 text-center ${
                  val >= 95 ? "bg-green-50 border-green-200" : val >= 85 ? "bg-yellow-50 border-yellow-200" : "bg-red-50 border-red-200"
                }`}
              >
                <p className="text-sm text-gray-500">{key}</p>
                <p className="text-3xl font-bold mt-1">{val}%</p>
              </div>
            ))}
          </div>
        )}

        {/* Batch Traceability */}
        <section className="bg-white rounded-xl border p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4">🔗 Batch Traceability</h2>
          <form onSubmit={handleTrace} className="flex gap-2 mb-4">
            <input
              type="text"
              value={batchCode}
              onChange={(e) => setBatchCode(e.target.value)}
              placeholder="e.g. PR-260329-1"
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-brand-500"
            />
            <button
              type="submit"
              className="px-4 py-2 bg-brand-500 text-white rounded-lg hover:bg-brand-600"
            >
              Trace
            </button>
          </form>
          {trace && (
            <div className="space-y-4">
              {trace.raw_materials.length > 0 && (
                <div>
                  <h3 className="font-medium mb-2">Raw Materials</h3>
                  <DataTable data={trace.raw_materials} />
                </div>
              )}
              {trace.production.length > 0 && (
                <div>
                  <h3 className="font-medium mb-2">Production</h3>
                  <DataTable data={trace.production} />
                </div>
              )}
              {trace.orders.length > 0 && (
                <div>
                  <h3 className="font-medium mb-2">Orders</h3>
                  <DataTable data={trace.orders} />
                </div>
              )}
            </div>
          )}
        </section>

        {/* Temperature */}
        <section className="bg-white rounded-xl border p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4">🌡️ Temperature Excursions (7d)</h2>
          {excursions.length > 0 ? (
            <DataTable data={excursions} />
          ) : (
            <p className="text-green-600">✅ No temperature excursions in the last 7 days</p>
          )}
        </section>

        {/* Allergens */}
        <section className="bg-white rounded-xl border p-6">
          <h2 className="text-lg font-semibold mb-4">⚠️ Allergen Matrix</h2>
          <DataTable data={allergens} />
        </section>
      </main>
    </div>
  );
}
