"use client";

import { ArrowDown } from "lucide-react";

const layers = [
  {
    id: "input",
    label: "Question",
    sub: "Natural language in",
    color: "bg-blue-500/10 border-blue-500/30 text-blue-400",
  },
  {
    id: "scout",
    label: "schema-scout",
    sub: "Map database, flag PII",
    color: "bg-violet-500/10 border-violet-500/30 text-violet-400",
  },
  {
    id: "steward",
    label: "sql-steward",
    sub: "Compile query from semantic layer",
    color: "bg-emerald-500/10 border-emerald-500/30 text-emerald-400",
  },
  {
    id: "sop",
    label: "sql-sop",
    sub: "Lint for safety patterns",
    color: "bg-amber-500/10 border-amber-500/30 text-amber-400",
  },
  {
    id: "warden",
    label: "query-warden",
    sub: "Role-based access check",
    color: "bg-orange-500/10 border-orange-500/30 text-orange-400",
  },
  {
    id: "pii",
    label: "pii-veil",
    sub: "Mask PII in results",
    color: "bg-pink-500/10 border-pink-500/30 text-pink-400",
  },
  {
    id: "db",
    label: "Your Database",
    sub: "Stays on-prem",
    color: "bg-cyan-500/10 border-cyan-500/30 text-cyan-400",
  },
];

const sidecar = [
  {
    id: "blackbox",
    label: "agent-blackbox",
    sub: "Tamper-evident audit log",
    color: "bg-red-500/10 border-red-500/30 text-red-400",
  },
  {
    id: "thread",
    label: "thread-recall",
    sub: "Memory across turns",
    color: "bg-indigo-500/10 border-indigo-500/30 text-indigo-400",
  },
  {
    id: "drift",
    label: "drift-gate",
    sub: "Schema change detection",
    color: "bg-yellow-500/10 border-yellow-500/30 text-yellow-400",
  },
  {
    id: "elenchus",
    label: "elenchus",
    sub: "Survey authoring & conducting",
    color: "bg-teal-500/10 border-teal-500/30 text-teal-400",
  },
];

function Node({ label, sub, color }: { label: string; sub: string; color: string }) {
  return (
    <div className={`rounded-lg border px-4 py-3 text-center ${color}`}>
      <div className="text-sm font-semibold">{label}</div>
      <div className="mt-0.5 text-[10px] opacity-70">{sub}</div>
    </div>
  );
}

export default function FlowDiagram() {
  return (
    <div className="space-y-8">
      <div>
        <h3 className="mb-3 text-xs font-medium uppercase tracking-wider text-zinc-500">
          Main Pipeline
        </h3>
        <div className="flex flex-col items-center gap-2">
          {layers.map((layer, i) => (
            <div key={layer.id} className="flex flex-col items-center">
              <Node label={layer.label} sub={layer.sub} color={layer.color} />
              {i < layers.length - 1 && (
                <ArrowDown className="my-1 h-4 w-4 text-zinc-600" />
              )}
            </div>
          ))}
        </div>
      </div>

      <div>
        <h3 className="mb-3 text-xs font-medium uppercase tracking-wider text-zinc-500">
          Sidecar Services
        </h3>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {sidecar.map((s) => (
            <Node key={s.id} label={s.label} sub={s.sub} color={s.color} />
          ))}
        </div>
      </div>
    </div>
  );
}
