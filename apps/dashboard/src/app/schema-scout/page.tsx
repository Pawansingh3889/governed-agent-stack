"use client";

import { useQuery } from "@tanstack/react-query";
import { getSchemaTables, getSchemaDrift } from "@/lib/api";
import { AlertTriangle, CheckCircle2 } from "lucide-react";

export default function SchemaScoutPage() {
  const tables = useQuery({
    queryKey: ["schema-tables"],
    queryFn: getSchemaTables,
    refetchInterval: 30000,
  });

  const drift = useQuery({
    queryKey: ["schema-drift"],
    queryFn: getSchemaDrift,
    refetchInterval: 30000,
  });

  const tableList = Array.isArray(tables.data) ? tables.data : [];

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-semibold text-white">schema-scout</h1>
        <p className="mt-1 text-sm text-zinc-500">
          Database mapping, relationship recovery, and PII flagging. The foundation everything
          else depends on.
        </p>
      </header>

      {tables.error || drift.error ? (
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-5">
          <div className="flex items-center gap-2 text-amber-400">
            <AlertTriangle className="h-4 w-4" />
            <span className="text-sm font-medium">schema-scout is not reachable</span>
          </div>
          <p className="mt-2 text-sm text-amber-500/80">
            Start the backend, then set NEXT_PUBLIC_SCOUT_URL. This page will show live data
            when it is up.
          </p>
        </div>
      ) : null}

      <section className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-medium text-zinc-400">Discovered Tables</h2>
            <span className="text-xs text-zinc-600">
              {tables.isLoading ? "scanning..." : `${tableList.length} tables`}
            </span>
          </div>
          {tables.isLoading ? (
            <div className="mt-4 space-y-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="h-6 animate-pulse rounded bg-zinc-800/60" />
              ))}
            </div>
          ) : tableList.length === 0 ? (
            <p className="mt-4 text-sm text-zinc-600">
              No tables yet. Run schema-scout against your database to populate this view.
            </p>
          ) : (
            <ul className="mt-4 divide-y divide-zinc-800">
              {tableList.slice(0, 20).map((t: { name: string; columns?: number; pii?: boolean }) => (
                <li key={t.name} className="flex items-center justify-between py-2">
                  <span className="font-mono text-sm text-zinc-300">{t.name}</span>
                  <span className="flex items-center gap-2 text-xs text-zinc-500">
                    {t.columns != null && <span>{t.columns} cols</span>}
                    {t.pii && (
                      <span className="rounded-full bg-pink-500/10 px-2 py-0.5 text-pink-400">
                        PII
                      </span>
                    )}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-medium text-zinc-400">drift-gate</h2>
            <span className="text-xs text-zinc-600">baseline vs live schema</span>
          </div>
          {drift.isLoading ? (
            <p className="mt-4 text-sm text-zinc-600">Checking drift...</p>
          ) : drift.error ? (
            <p className="mt-4 text-sm text-zinc-600">Not reachable.</p>
          ) : (
            <div className="mt-4">
              <div className="flex items-center gap-2">
                {drift.data?.drifted ? (
                  <AlertTriangle className="h-5 w-5 text-red-400" />
                ) : (
                  <CheckCircle2 className="h-5 w-5 text-emerald-400" />
                )}
                <span className="text-sm text-zinc-300">
                  {drift.data?.drifted ? "Schema has drifted" : "Schema matches baseline"}
                </span>
              </div>
              {drift.data?.changes?.length > 0 && (
                <ul className="mt-3 space-y-1.5">
                  {drift.data.changes.map((c: string, i: number) => (
                    <li key={i} className="font-mono text-xs text-red-400">
                      {c}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
