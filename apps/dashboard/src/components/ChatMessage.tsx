"use client";

import ReactMarkdown from "react-markdown";

interface ChatMessageProps {
  role: "user" | "assistant";
  content: string;
  sql?: string;
  data?: Record<string, unknown>[];
  error?: boolean;
}

export function ChatMessage({ role, content, sql, data, error }: ChatMessageProps) {
  const isUser = role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 ${
          isUser
            ? "bg-brand-600 text-white"
            : error
            ? "border border-red-500/30 bg-red-500/10 text-red-300"
            : "border border-zinc-800 bg-zinc-900 text-zinc-200"
        }`}
      >
        <div className="prose prose-sm prose-invert max-w-none">
          <ReactMarkdown>{content}</ReactMarkdown>
        </div>

        {sql && (
          <details className="mt-2">
            <summary className="cursor-pointer text-xs opacity-70 hover:opacity-100">
              View SQL
            </summary>
            <pre className="mt-1 overflow-x-auto rounded bg-black/40 p-2 text-xs text-zinc-300">
              {sql}
            </pre>
          </details>
        )}

        {data && data.length > 0 && (
          <div className="mt-2 overflow-x-auto">
            <table className="min-w-full text-xs">
              <thead>
                <tr>
                  {Object.keys(data[0]).map((key) => (
                    <th
                      key={key}
                      className="border-b border-white/10 px-2 py-1 text-left font-medium"
                    >
                      {key}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.slice(0, 20).map((row, i) => (
                  <tr key={i}>
                    {Object.values(row).map((val, j) => (
                      <td key={j} className="border-b border-white/5 px-2 py-1">
                        {String(val)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}