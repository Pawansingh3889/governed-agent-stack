"use client";

import { useQuery } from "@tanstack/react-query";
import StatusCard from "@/components/StatusCard";
import { getComponentStatuses } from "@/lib/api";
import { Activity, Boxes, Shield } from "lucide-react";

export default function OverviewPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["statuses"],
    queryFn: getComponentStatuses,
    refetchInterval: 15000,
  });

  const onlineCount = data?.filter((c) => c.online).length ?? 0;

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-semibold text-white">Overview</h1>
        <p className="mt-1 text-sm text-zinc-500">
          End-to-end view of every component in the Governed Agent Stack.
        </p>
      </header>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
          <div className="flex items-center gap-2 text-zinc-400">
            <Boxes className="h-4 w-4" />
            <span className="text-xs font-medium uppercase tracking-wider">Components</span>
          </div>
          <p className="mt-2 text-2xl font-semibold text-white">13</p>
          <p className="text-xs text-zinc-500">Across packages/ and apps/</p>
        </div>
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
          <div className="flex items-center gap-2 text-zinc-400">
            <Activity className="h-4 w-4" />
            <span className="text-xs font-medium uppercase tracking-wider">Online</span>
          </div>
          <p className="mt-2 text-2xl font-semibold text-emerald-400">
            {isLoading ? "..." : onlineCount}
          </p>
          <p className="text-xs text-zinc-500">
            {isError ? "Health check failed" : "of 5 health-checked components"}
          </p>
        </div>
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
          <div className="flex items-center gap-2 text-zinc-400">
            <Shield className="h-4 w-4" />
            <span className="text-xs font-medium uppercase tracking-wider">Governance</span>
          </div>
          <p className="mt-2 text-2xl font-semibold text-white">Active</p>
          <p className="text-xs text-zinc-500">Role checks, masking, audit enabled</p>
        </div>
      </div>

      <section>
        <h2 className="mb-3 text-sm font-medium text-zinc-400">Component Health</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {isLoading &&
            Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="h-28 animate-pulse rounded-xl border border-zinc-800 bg-zinc-900/30" />
            ))}
          {data?.map((c) => (
            <StatusCard key={c.name} {...c} />
          ))}
        </div>
        {isError && (
          <p className="mt-4 text-sm text-amber-400">
            Some health checks failed. Components may not be running.
          </p>
        )}
      </section>

      <section className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
        <h2 className="mb-2 text-sm font-medium text-zinc-400">How it works</h2>
        <p className="text-sm leading-6 text-zinc-500">
          A question in plain English enters FloorMind, which turns it into SQL.
          schema-scout supplies the catalog so the agent knows the schema.
          sql-sop lints the query, query-warden checks roles, pii-veil masks
          results, and agent-blackbox records every step. drift-gate keeps the
          catalog honest, thread-recall carries memory, and elenchus handles
          governed surveys.
        </p>
      </section>
    </div>
  );
}
