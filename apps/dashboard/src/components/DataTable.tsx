"use client";

interface DataTableProps {
  data: Record<string, unknown>[];
  maxRows?: number;
}

export function DataTable({ data, maxRows = 50 }: DataTableProps) {
  if (!data || data.length === 0) {
    return <p className="text-sm italic text-zinc-500">No data</p>;
  }

  const headers = Object.keys(data[0]);
  const rows = data.slice(0, maxRows);

  return (
    <div className="overflow-x-auto rounded-lg border border-zinc-800">
      <table className="min-w-full text-sm">
        <thead className="bg-zinc-900">
          <tr>
            {headers.map((h) => (
              <th
                key={h}
                className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wider text-zinc-400"
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-800 bg-zinc-950/50">
          {rows.map((row, i) => (
            <tr key={i} className="hover:bg-zinc-900">
              {headers.map((h) => (
                <td key={h} className="whitespace-nowrap px-3 py-2 text-zinc-300">
                  {String(row[h] ?? "")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {data.length > maxRows && (
        <p className="p-2 text-xs text-zinc-500">
          Showing {maxRows} of {data.length} rows
        </p>
      )}
    </div>
  );
}