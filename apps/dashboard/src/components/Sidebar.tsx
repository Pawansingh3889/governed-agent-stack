"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  GitBranch,
  Database,
  Shield,
  ClipboardList,
  ScrollText,
  Settings,
} from "lucide-react";

const nav = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/flow", label: "Agent Flow", icon: GitBranch },
  { href: "/schema-scout", label: "Schema Scout", icon: Database },
  { href: "/sql-steward", label: "SQL Steward", icon: Shield },
  { href: "/surveys", label: "Surveys", icon: ClipboardList },
  { href: "/audit", label: "Audit Log", icon: ScrollText },
  { href: "/config", label: "Configuration", icon: Settings },
];

export default function Sidebar() {
  const path = usePathname();

  return (
    <aside className="fixed inset-y-0 left-0 z-50 w-64 border-r border-zinc-800 bg-zinc-950 flex flex-col">
      <div className="flex h-14 items-center gap-2 border-b border-zinc-800 px-5">
        <Shield className="h-5 w-5 text-emerald-500" />
        <span className="text-sm font-semibold text-white">Governed Agent Stack</span>
      </div>
      <nav className="flex-1 space-y-1 p-3">
        {nav.map(({ href, label, icon: Icon }) => {
          const active = path === href;
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors ${
                active
                  ? "bg-emerald-500/10 text-emerald-400"
                  : "text-zinc-400 hover:bg-zinc-800 hover:text-white"
              }`}
            >
              <Icon className="h-4 w-4" />
              {label}
            </Link>
          );
        })}
      </nav>
      <div className="border-t border-zinc-800 p-4">
        <p className="text-[10px] text-zinc-600">govern-agents/governed-agent-stack</p>
      </div>
    </aside>
  );
}
