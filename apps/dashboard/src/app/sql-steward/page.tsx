"use client";

import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { getSqlStewardEntities, lintSql } from "@/lib/api";
import { AlertTriangle, CheckCircle2, Loader2, TerminalSquare } from "lucide-react";

export default function SqlStewardPage() {
  const [sql, setSql] = useState("");
  const [lintResult, setLintResult] = useState<{ passed?: boolean; findings?: unknown[] } | null>(null);

  const entities = useQuery({
    queryKey: ["steward-entities"],
    queryFn: getSqlStewardEntities,
    refetchInterval: 30000,
  });

  const lint = useMutation({
    mutationFn: lintSql,
    onSuccess: setLintResult,
  });

  const entityList = Array.isArray(entities.data) ? entities.data : [];

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-semibold text-white">sql-steward</h1>
        <p className="mt-1 text-sm text-zinc-500">
          The flagship. Compiles queries from a semantic layer you control, so the agent never
          writes SQL at all.
        </p>
      </header>

      {entities.error ? (
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-5">
          <div className="flex items-center gap-2 text-amber-400">
            <AlertTriangle className="h-4 w-4" />
            <span className="text-sm font-medium">sql-steward is not reachable</span>
          </div>
          <p className="mt-2 text-sm text-amber-500/80">
            Start the sql-steward MCP server, then set NEXT_PUBLIC_SQL_STEWARD_URL.
          </p>
        </div>
      ) : null}

      <section className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
          <h2 className="text-sm font-medium text-zinc-400">Semantic Layer</h2>
          <p className="mt-1 text-xs text-zinc-600">
            Entities the agent may query, with joins and metrics defined by you.
          </p>
          {entities.isLoading ? (
            <div className="mt-4 space-y-2">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="h-6 animate-pulse rounded bg-zinc-800/60" />
              ))}
            </div>
          ) : entityList.length === 0 ? (
            <p className="mt-4 text-sm text-zinc-600">No entities loaded yet.</p>
          ) : (
            <ul className="mt-4 divide-y divide-zinc-800">
              {entityList.slice(0, 15).map((e: { name: string; table?: string }) => (
                <li key={e.name} className="flex items-center justify-between py-2">
                  <span className="text-sm text-zinc-300">{e.name}</span>
                  {e.table && <span className="font-mono text-xs text-zinc-600">{e.table}</span>}
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
          <h2 className="text-sm font-medium text-zinc-400">Query Lint</h2>
          <p className="mt-1 text-xs text-zinc-600">
            Check a query against sql-sop rules before it runs.
          </p>
          <textarea
            value={sql}
            onChange={(e) => setSql(e.target.value)}
            placeholder="SELECT * FROM orders WHERE customer_id = 1;"
            className="mt-3 w-full rounded-lg border border-zinc-700 bg-zinc-950 p-3 font-mono text-sm text-zinc-200 outline-none placeholder:text-zinc-700 focus:border-emerald-500"
            rows={4}
          />
          <button
            onClick={() => sql && lint.mutate(sql)}
            disabled={!sql || lint.isPending}
            className="mt-3 inline-flex items-center gap-2 rounded-lg bg-emerald-500 px-4 py-2 text-sm font-medium text-zinc-950 transition-colors hover:bg-emerald-400 disabled:opacity-50"
          >
            {lint.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <TerminalSquare className="h-4 w-4" />}
            Lint query
          </button>

          {lint.isError && (
            <div className="mt-4 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-400">
              Lint request failed. sql-steward may not be running.
            </div>
          )}

          {lintResult && !lint.isError && (
            <div className="mt-4 rounded-lg border border-zinc-800 bg-zinc-950 p-3">
              {lintResult.passed ? (
                <div className="flex items-center gap-2 text-emerald-400">
                  <CheckCircle2 className="h-4 w-4" />
                  <span className="text-sm font-medium">Query passed lint</span>
                </div>
              ) : (
                <div className="flex items-center gap-2 text-red-400">
                  <AlertTriangle className="h-4 w-4" />
                  <span className="text-sm font-medium">Query failed lint</span>
                </div>
              )}
              <ul className="mt-2 space-y-1">
                {(lintResult.findings ?? []).map((f, i) => {
                  const finding = f as { rule_id?: string; message?: string };
                  return (
                    <li key={i} className="font-mono text-xs text-zinc-500">
                      [{finding.rule_id}] {finding.message}
                    </li>
                  );
                })}
              </ul>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
