interface KPICardProps {
  label: string;
  value: string | number;
  sublabel?: string;
  color?: "default" | "danger" | "success";
}

export function KPICard({ label, value, sublabel, color = "default" }: KPICardProps) {
  const colorClasses = {
    default: "bg-white",
    danger: "bg-red-50 border-red-200",
    success: "bg-green-50 border-green-200",
  };

  return (
    <div
      className={`rounded-xl border border-gray-200 p-4 ${colorClasses[color]}`}
    >
      <p className="text-sm text-gray-500">{label}</p>
      <p className="text-2xl font-bold mt-1">{value}</p>
      {sublabel && <p className="text-xs text-gray-400 mt-1">{sublabel}</p>}
    </div>
  );
}
