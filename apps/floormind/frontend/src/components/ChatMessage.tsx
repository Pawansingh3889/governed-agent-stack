"use client";

import ReactMarkdown from "react-markdown";

interface ChatMessageProps {
  role: "user" | "assistant";
  content: string;
  sql?: string;
  data?: Record<string, unknown>[];
  error?: boolean;
}

export function ChatMessage({
  role,
  content,
  sql,
  data,
  error,
}: ChatMessageProps) {
  const isUser = role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 ${
          isUser
            ? "bg-brand-500 text-white"
            : error
            ? "bg-red-50 text-red-800 border border-red-200"
            : "bg-gray-100 text-gray-900"
        }`}
      >
        <div className="prose prose-sm max-w-none">
          <ReactMarkdown>{content}</ReactMarkdown>
        </div>

        {sql && (
          <details className="mt-2">
            <summary className="cursor-pointer text-xs opacity-70 hover:opacity-100">
              View SQL
            </summary>
            <pre className="mt-1 p-2 bg-black/10 rounded text-xs overflow-x-auto">
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
                      className="px-2 py-1 text-left font-medium border-b border-black/10"
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
                      <td key={j} className="px-2 py-1 border-b border-black/5">
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
