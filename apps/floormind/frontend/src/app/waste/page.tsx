"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getWasteSummary, getYieldByProduct, predictWaste } from "@/lib/api";
import { Sidebar } from "@/components/Sidebar";
import { DataTable } from "@/components/DataTable";
import { KPICard } from "@/components/KPICard";

export default function WastePage() {
  const [wasteData, setWasteData] = useState<Record<string, unknown>[]>([]);
  const [yieldData, setYieldData] = useState<Record<string, unknown>[]>([]);
  const [predProduct, setPredProduct] = useState("Product A");
  const [predInput, setPredInput] = useState("500");
  const [prediction, setPrediction] = useState<Record<string, unknown> | null>(null);
  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem("fm_token");
    if (!token) { router.push("/"); return; }
    getWasteSummary(7).then(setWasteData).catch(console.error);
    getYieldByProduct(30).then(setYieldData).catch(console.error);
  }, [router]);

  const handlePredict = async (e: FormEvent) => {
    e.preventDefault();
    const result = await predictWaste(predProduct, parseFloat(predInput));
    setPrediction(result);
  };

  const totalWasteCost = yieldData.reduce(
    (sum, r) => sum + (Number(r.waste_cost_gbp) || 0),
    0
  );

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-6 pb-20 md:pb-6 max-w-6xl">
        <h1 className="text-2xl font-bold mb-6">📈 Yield & Waste Analysis</h1>

        <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-8">
          <KPICard label="Waste (7d)" value={wasteData.length > 0 ? `${wasteData.reduce((s, r) => s + Number(r.total_kg || 0), 0).toLocaleString()} kg` : "—"} />
          <KPICard label="Total Waste Cost (30d)" value={`£${totalWasteCost.toLocaleString()}`} color="danger" />
          <KPICard label="Products Tracked" value={yieldData.length || "—"} />
        </div>

        {/* Yield by Product */}
        <section className="bg-white rounded-xl border p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4">Yield by Product (30d)</h2>
          <DataTable data={yieldData} />
        </section>

        {/* Waste Breakdown */}
        <section className="bg-white rounded-xl border p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4">Waste Breakdown (7d)</h2>
          <DataTable data={wasteData} />
        </section>

        {/* Predictor */}
        <section className="bg-white rounded-xl border p-6">
          <h2 className="text-lg font-semibold mb-4">🔮 Waste Predictor</h2>
          <form onSubmit={handlePredict} className="flex flex-wrap gap-3 mb-4">
            <input
              type="text"
              value={predProduct}
              onChange={(e) => setPredProduct(e.target.value)}
              placeholder="Product name"
              className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-brand-500"
            />
            <input
              type="number"
              value={predInput}
              onChange={(e) => setPredInput(e.target.value)}
              placeholder="Input kg"
              className="w-32 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-brand-500"
            />
            <button
              type="submit"
              className="px-4 py-2 bg-brand-500 text-white rounded-lg hover:bg-brand-600"
            >
              Predict
            </button>
          </form>
          {prediction && (
            <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
              <p>
                Expected output: <strong>{prediction.expected_output_kg} kg</strong> |
                Waste: <strong>{prediction.expected_waste_kg} kg</strong> |
                Yield: <strong>{prediction.expected_yield_pct}%</strong>
              </p>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
