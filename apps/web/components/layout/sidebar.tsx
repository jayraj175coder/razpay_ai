"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  FolderGit2,
  Sliders,
  CalendarCheck,
  UserCheck,
  ShieldAlert,
  History,
  TrendingUp,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navigation = [
  { name: "Command Center", href: "/dashboard", icon: LayoutDashboard },
  { name: "Case Queue", href: "/recovery", icon: FolderGit2 },
  { name: "Simulation Benchmark", href: "/simulation", icon: Sliders },
  { name: "Promise-to-Pay", href: "/promises", icon: CalendarCheck },
  { name: "Human Approvals", href: "/approvals", icon: UserCheck },
  { name: "Policy Engine", href: "/policies", icon: ShieldAlert },
  { name: "Audit Trail", href: "/audit", icon: History },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed inset-y-0 left-0 z-30 flex w-64 flex-col border-r border-slate-800 bg-[#090d16]/95 backdrop-blur-md">
      {/* Brand Header */}
      <div className="flex h-16 items-center gap-3 border-b border-slate-800 px-6">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 font-bold">
          <TrendingUp className="h-5 w-5" />
        </div>
        <div>
          <span className="text-base font-bold tracking-tight text-white">Recover<span className="text-emerald-400">AI</span></span>
          <span className="block text-[10px] uppercase font-mono tracking-wider text-slate-400">Revenue Agent</span>
        </div>
      </div>

      {/* Nav List */}
      <div className="flex flex-1 flex-col justify-between overflow-y-auto px-3 py-4">
        <nav className="space-y-1">
          {navigation.map((item) => {
            const isActive = pathname === item.href || pathname?.startsWith(`${item.href}/`);
            return (
              <Link
                key={item.name}
                href={item.href}
                className={cn(
                  "group flex items-center gap-3 rounded-md px-3 py-2 text-xs font-medium transition-colors",
                  isActive
                    ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-semibold"
                    : "text-slate-400 hover:bg-slate-800/60 hover:text-slate-200"
                )}
              >
                <item.icon
                  className={cn(
                    "h-4 w-4 shrink-0 transition-colors",
                    isActive ? "text-emerald-400" : "text-slate-400 group-hover:text-slate-300"
                  )}
                />
                {item.name}
              </Link>
            );
          })}
        </nav>

        {/* Footer info */}
        <div className="rounded-lg border border-slate-800/80 bg-slate-900/50 p-3 text-[11px] text-slate-400">
          <div className="flex items-center gap-2 font-medium text-slate-300 mb-1">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            Active Mode: Sandbox
          </div>
          <p className="text-[10px] text-slate-400 font-mono">
            Provider: Mock & Razorpay
          </p>
        </div>
      </div>
    </aside>
  );
}
