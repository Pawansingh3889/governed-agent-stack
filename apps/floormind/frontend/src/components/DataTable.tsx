"use client";

interface DataTableProps {
  data: Record<string, unknown>[];
  maxRows?: number;
}

export function DataTable({ data, maxRows = 50 }: DataTableProps) {
  if (!data || data.length === 0) {
    return <p className="text-sm text-gray-400 italic">No data</p>;
  }

  const headers = Object.keys(data[0]);
  const rows = data.slice(0, maxRows);

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200">
      <table className="min-w-full text-sm">
        <thead className="bg-gray-50">
          <tr>
            {headers.map((h) => (
              <th
                key={h}
                className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-100">
          {rows.map((row, i) => (
            <tr key={i} className="hover:bg-gray-50">
              {headers.map((h) => (
                <td key={h} className="px-3 py-2 whitespace-nowrap">
                  {String(row[h] ?? "")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {data.length > maxRows && (
        <p className="text-xs text-gray-400 p-2">
          Showing {maxRows} of {data.length} rows
        </p>
      )}
    </div>
  );
}
