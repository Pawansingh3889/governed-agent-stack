interface KPICardProps {
  label: string;
  value: string | number;
  sublabel?: string;
  color?: "default" | "danger" | "success";
}

export function KPICard({ label, value, sublabel, color = "default" }: KPICardProps) {
  const colorClasses = {
    default: "border-zinc-800 bg-zinc-900/50",
    danger: "border-red-500/30 bg-red-500/10",
    success: "border-green-500/30 bg-green-500/10",
  };

  return (
    <div className={`rounded-xl border p-4 ${colorClasses[color]}`}>
      <p className="text-sm text-zinc-400">{label}</p>
      <p className="mt-1 text-2xl font-bold text-white">{value}</p>
      {sublabel && <p className="mt-1 text-xs text-zinc-500">{sublabel}</p>}
    </div>
  );
}