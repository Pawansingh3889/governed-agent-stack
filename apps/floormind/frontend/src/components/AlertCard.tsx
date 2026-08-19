"use client";

interface AlertCardProps {
  level: "critical" | "warning" | "info";
  title: string;
  message: string;
  category: string;
}

const LEVEL_STYLES = {
  critical: "bg-red-50 border-red-200 text-red-800",
  warning: "bg-yellow-50 border-yellow-200 text-yellow-800",
  info: "bg-blue-50 border-blue-200 text-blue-800",
};

const LEVEL_ICONS = {
  critical: "🔴",
  warning: "🟡",
  info: "🔵",
};

export function AlertCard({ level, title, message, category }: AlertCardProps) {
  return (
    <div className={`rounded-xl border p-4 ${LEVEL_STYLES[level]}`}>
      <div className="flex items-start gap-3">
        <span className="text-lg">{LEVEL_ICONS[level]}</span>
        <div className="flex-1">
          <h3 className="font-semibold">{title}</h3>
          <p className="text-sm mt-1 opacity-80">{message}</p>
          <p className="text-xs mt-2 opacity-50">Category: {category}</p>
        </div>
      </div>
    </div>
  );
}
