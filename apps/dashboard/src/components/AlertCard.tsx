"use client";

interface AlertCardProps {
  level: "critical" | "warning" | "info";
  title: string;
  message: string;
  category: string;
}

const LEVEL_STYLES = {
  critical: "border-red-500/40 bg-red-500/10 text-red-300",
  warning: "border-yellow-500/40 bg-yellow-500/10 text-yellow-300",
  info: "border-blue-500/40 bg-blue-500/10 text-blue-300",
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
          <p className="mt-1 text-sm opacity-80">{message}</p>
          <p className="mt-2 text-xs opacity-50">Category: {category}</p>
        </div>
      </div>
    </div>
  );
}