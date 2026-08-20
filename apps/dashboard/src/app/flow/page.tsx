import FlowDiagram from "@/components/FlowDiagram";

export default function FlowPage() {
  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-white">Agent Flow</h1>
        <p className="mt-1 text-sm text-zinc-500">
          How a question moves through the governed stack, and the services that keep it
            honest.
        </p>
      </header>

      <FlowDiagram />

      <section className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
        <h2 className="mb-3 text-sm font-medium text-zinc-400">Step by step</h2>
        <ol className="list-decimal space-y-2 pl-5 text-sm text-zinc-500">
          <li>
            <span className="text-zinc-300">schema-scout</span> maps the database, recovers
            hidden foreign keys, and flags PII columns.
          </li>
          <li>
            <span className="text-zinc-300">FloorMind</span> turns the natural-language
            question into a candidate SQL query using the catalog.
          </li>
          <li>
            <span className="text-zinc-300">sql-sop</span> lints the query for dangerous or
            slow patterns and refuses anything with severity <code>error</code>.
          </li>
          <li>
            <span className="text-zinc-300">query-warden</span> checks that the asker&apos;s role
            may touch every table and column referenced.
          </li>
          <li>
            <span className="text-zinc-300">sql-explorer-mcp</span> runs the query read-only.
          </li>
          <li>
            <span className="text-zinc-300">pii-veil</span> masks any PII in result rows.
          </li>
          <li>
            <span className="text-zinc-300">agent-blackbox</span> appends the whole step to
            the hash-chained audit ledger.
          </li>
        </ol>
      </section>
    </div>
  );
}
