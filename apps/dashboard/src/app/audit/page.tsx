"use client";

import { useQuery } from "@tanstack/react-query";
import { getAuditLogs } from "@/lib/api";
import { AlertTriangle, ScrollText } from "lucide-react";

interface AuditEntry {
  id?: string;
  hash?: string;
  prev_hash?: string;
  actor?: string;
  action?: string;
  target?: string;
  timestamp?: string;
}

export default function AuditPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["audit-logs"],
    queryFn: getAuditLogs,
    refetchInterval: 15000,
  });

  const entries = Array.isArray(data) ? data : [];

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-semibold text-white">Audit Log</h1>
        <p className="mt-1 text-sm text-zinc-500">
          Tamper-evident, hash-chained ledger from agent-blackbox. Every step an agent takes,
          verifiable later.
        </p>
      </header>

      {error ? (
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-5">
          <div className="flex items-center gap-2 text-amber-400">
            <AlertTriangle className="h-4 w-4" />
            <span className="text-sm font-medium">agent-blackbox is not reachable</span>
          </div>
          <p className="mt-2 text-sm text-amber-500/80">
            Start the ledger, then set NEXT_PUBLIC_BLACKBOX_URL.
          </p>
        </div>
      ) : null}

      <section>
        <h2 className="mb-3 text-sm font-medium text-zinc-400">Ledger Entries</h2>
        {isLoading ? (
          <div className="space-y-2">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="h-12 animate-pulse rounded-xl border border-zinc-800 bg-zinc-900/30" />
            ))}
          </div>
        ) : entries.length === 0 ? (
          <div className="rounded-xl border border-dashed border-zinc-800 p-8 text-center">
            <ScrollText className="mx-auto h-8 w-8 text-zinc-700" />
            <p className="mt-3 text-sm text-zinc-500">No audit entries yet.</p>
            <p className="mt-1 text-xs text-zinc-600">
              Entries appear here as soon as agent actions are recorded.
            </p>
          </div>
        ) : (
          <div className="overflow-hidden rounded-xl border border-zinc-800">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-zinc-800 bg-zinc-900/80">
                <tr className="text-xs uppercase tracking-wider text-zinc-500">
                  <th className="px-4 py-3">Action</th>
                  <th className="px-4 py-3">Actor</th>
                  <th className="px-4 py-3">Target</th>
                  <th className="px-4 py-3">Timestamp</th>
                  <th className="px-4 py-3">Hash</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800">
                {entries.slice(0, 30).map((e: AuditEntry, i) => (
                  <tr key={e.id ?? i} className="bg-zinc-950/40 hover:bg-zinc-900/60">
                    <td className="px-4 py-3 font-medium text-zinc-300">{e.action ?? "-"}</td>
                    <td className="px-4 py-3 text-zinc-500">{e.actor ?? "-"}</td>
                    <td className="px-4 py-3 text-zinc-500">{e.target ?? "-"}</td>
                    <td className="px-4 py-3 text-xs text-zinc-500">
                      {e.timestamp ? new Date(e.timestamp).toLocaleString() : "-"}
                    </td>
                    <td className="px-4 py-3 font-mono text-[10px] text-zinc-600">
                      {(e.hash ?? "").slice(0, 12)}...
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}