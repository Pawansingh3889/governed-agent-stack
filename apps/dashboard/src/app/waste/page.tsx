"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getWasteSummary, getYieldByProduct, predictWaste } from "@/lib/floor";
import { useAuth } from "@/hooks/useAuth";
import { DataTable } from "@/components/DataTable";
import { KPICard } from "@/components/KPICard";

export default function WastePage() {
  const [wasteData, setWasteData] = useState<Record<string, unknown>[]>([]);
  const [yieldData, setYieldData] = useState<Record<string, unknown>[]>([]);
  const [predProduct, setPredProduct] = useState("Product A");
  const [predInput, setPredInput] = useState("500");
  const [prediction, setPrediction] = useState<Record<string, unknown> | null>(null);
  const { gate } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (gate === "login") {
      router.push("/login");
      return;
    }
    if (gate !== "ok") return;
    getWasteSummary(7).then(setWasteData).catch(console.error);
    getYieldByProduct(30).then(setYieldData).catch(console.error);
  }, [gate, router]);

  const handlePredict = async (e: FormEvent) => {
    e.preventDefault();
    const result = await predictWaste(predProduct, parseFloat(predInput));
    setPrediction(result);
  };

  const totalWasteCost = yieldData.reduce(
    (sum, r) => sum + (Number(r.waste_cost_gbp) || 0),
    0
  );

  if (gate !== "ok") return null;

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-semibold text-white">Yield & Waste Analysis</h1>
        <p className="mt-1 text-sm text-zinc-500">
          Waste breakdown, yields and the predictor from FloorMind
        </p>
      </header>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
        <KPICard
          label="Waste (7d)"
          value={
            wasteData.length > 0
              ? `${wasteData.reduce((s, r) => s + Number(r.total_kg || 0), 0).toLocaleString()} kg`
              : "—"
          }
        />
        <KPICard
          label="Total Waste Cost (30d)"
          value={`£${totalWasteCost.toLocaleString()}`}
          color="danger"
        />
        <KPICard label="Products Tracked" value={yieldData.length || "—"} />
      </div>

      <section className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-6">
        <h2 className="mb-4 text-lg font-semibold text-white">Yield by Product (30d)</h2>
        <DataTable data={yieldData} />
      </section>

      <section className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-6">
        <h2 className="mb-4 text-lg font-semibold text-white">Waste Breakdown (7d)</h2>
        <DataTable data={wasteData} />
      </section>

      <section className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-6">
        <h2 className="mb-4 text-lg font-semibold text-white">Waste Predictor</h2>
        <form onSubmit={handlePredict} className="mb-4 flex flex-wrap gap-3">
          <input
            type="text"
            value={predProduct}
            onChange={(e) => setPredProduct(e.target.value)}
            placeholder="Product name"
            className="rounded-lg border border-zinc-700 bg-zinc-950 px-4 py-2 text-sm text-zinc-200 placeholder-zinc-500 focus:border-transparent focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
          <input
            type="number"
            value={predInput}
            onChange={(e) => setPredInput(e.target.value)}
            placeholder="Input kg"
            className="w-32 rounded-lg border border-zinc-700 bg-zinc-950 px-4 py-2 text-sm text-zinc-200 placeholder-zinc-500 focus:border-transparent focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
          <button
            type="submit"
            className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-600"
          >
            Predict
          </button>
        </form>
        {prediction && (
          <div className="rounded-lg border border-green-500/30 bg-green-500/10 p-4 text-sm text-green-300">
            Expected output: <strong>{String(prediction.expected_output_kg)} kg</strong> | Waste:{" "}
            <strong>{String(prediction.expected_waste_kg)} kg</strong> | Yield:{" "}
            <strong>{String(prediction.expected_yield_pct)}%</strong>
          </div>
        )}
      </section>
    </div>
  );
}