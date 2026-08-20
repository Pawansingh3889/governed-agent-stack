"use client";

import { useState } from "react";
import { Check, Copy } from "lucide-react";

const envVars = [
  { key: "NEXT_PUBLIC_SCOUT_URL", desc: "schema-scout backend", value: "http://localhost:8080" },
  { key: "NEXT_PUBLIC_SQL_STEWARD_URL", desc: "sql-steward MCP server", value: "http://localhost:8081" },
  { key: "NEXT_PUBLIC_ELENCHUS_URL", desc: "elenchus backend", value: "http://localhost:8000" },
  { key: "NEXT_PUBLIC_BLACKBOX_URL", desc: "agent-blackbox ledger", value: "http://localhost:8082" },
];

const composeYml = `services:
  schema-scout:
    build: ./packages/schema-scout
    ports: ["8080:8080"]
  sql-steward:
    build: ./packages/sql-steward
    ports: ["8081:8080"]
  elenchus:
    build: ./apps/elenchus
    ports: ["8000:8000"]
  agent-blackbox:
    build: ./packages/agent-blackbox
    ports: ["8082:8080"]
`;

export default function ConfigPage() {
  const [copied, setCopied] = useState<string | null>(null);

  const copy = async (text: string, id: string) => {
    await navigator.clipboard.writeText(text);
    setCopied(id);
    setTimeout(() => setCopied(null), 1500);
  };

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-semibold text-white">Configuration</h1>
        <p className="mt-1 text-sm text-zinc-500">
          Where each component is expected to run, and how to wire them together.
        </p>
      </header>

      <section>
        <h2 className="mb-3 text-sm font-medium text-zinc-400">Environment Variables</h2>
        <div className="overflow-hidden rounded-xl border border-zinc-800">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-zinc-800 bg-zinc-900/80">
              <tr className="text-xs uppercase tracking-wider text-zinc-500">
                <th className="px-4 py-3">Variable</th>
                <th className="px-4 py-3">Purpose</th>
                <th className="px-4 py-3">Default</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800">
              {envVars.map((v) => (
                <tr key={v.key} className="bg-zinc-950/40 hover:bg-zinc-900/60">
                  <td className="px-4 py-3">
                    <code className="font-mono text-xs text-emerald-400">{v.key}</code>
                  </td>
                  <td className="px-4 py-3 text-zinc-500">{v.desc}</td>
                  <td className="px-4 py-3 font-mono text-xs text-zinc-400">{v.value}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-medium text-zinc-400">Compose Wiring</h2>
          <button
            onClick={() => copy(composeYml, "compose")}
            className="inline-flex items-center gap-1.5 rounded-md border border-zinc-700 px-2.5 py-1.5 text-xs text-zinc-300 transition-colors hover:bg-zinc-800"
          >
            {copied === "compose" ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
            {copied === "compose" ? "Copied" : "Copy"}
          </button>
        </div>
        <pre className="overflow-x-auto rounded-xl border border-zinc-800 bg-zinc-950 p-5 text-xs leading-5 text-zinc-400">
          {composeYml}
        </pre>
      </section>
    </div>
  );
}