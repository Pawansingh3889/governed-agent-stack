"use client";

import { CheckCircle, XCircle } from "lucide-react";

interface StatusCardProps {
  name: string;
  role: string;
  online: boolean;
}

export default function StatusCard({ name, role, online }: StatusCardProps) {
  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5 transition-colors hover:border-zinc-700">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-sm font-semibold text-white">{name}</h3>
          <p className="mt-1 text-xs text-zinc-500">{role}</p>
        </div>
        {online ? (
          <CheckCircle className="h-5 w-5 text-emerald-500" />
        ) : (
          <XCircle className="h-5 w-5 text-red-500" />
        )}
      </div>
      <div className="mt-3">
        <span
          className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium ${
            online
              ? "bg-emerald-500/10 text-emerald-400"
              : "bg-red-500/10 text-red-400"
          }`}
        >
          {online ? "Online" : "Offline"}
        </span>
      </div>
    </div>
  );
}
