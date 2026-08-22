import React from "react";
import { cn } from "@/lib/utils";
import { LucideIcon } from "lucide-react";

interface KPICardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  variant?: "default" | "emerald" | "amber" | "crimson" | "blue";
  badge?: string;
}

export function KPICard({
  title,
  value,
  subtitle,
  icon: Icon,
  variant = "default",
  badge,
}: KPICardProps) {
  const variantStyles = {
    default: {
      border: "border-slate-800",
      bg: "bg-slate-900/40",
      iconColor: "text-slate-400",
      iconBg: "bg-slate-800/60",
      valColor: "text-white",
    },
    emerald: {
      border: "border-emerald-500/20",
      bg: "bg-emerald-500/[0.03]",
      iconColor: "text-emerald-400",
      iconBg: "bg-emerald-500/10",
      valColor: "text-emerald-400",
    },
    amber: {
      border: "border-amber-500/20",
      bg: "bg-amber-500/[0.03]",
      iconColor: "text-amber-400",
      iconBg: "bg-amber-500/10",
      valColor: "text-amber-300",
    },
    crimson: {
      border: "border-rose-500/20",
      bg: "bg-rose-500/[0.03]",
      iconColor: "text-rose-400",
      iconBg: "bg-rose-500/10",
      valColor: "text-rose-300",
    },
    blue: {
      border: "border-blue-500/20",
      bg: "bg-blue-500/[0.03]",
      iconColor: "text-blue-400",
      iconBg: "bg-blue-500/10",
      valColor: "text-blue-300",
    },
  }[variant];

  return (
    <div
      className={cn(
        "relative flex flex-col justify-between rounded-xl border p-5 transition hover:border-slate-700 backdrop-blur-sm",
        variantStyles.border,
        variantStyles.bg
      )}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium uppercase tracking-wider text-slate-400">
          {title}
        </span>
        <div className={cn("flex h-8 w-8 items-center justify-center rounded-lg border border-slate-700/50", variantStyles.iconBg)}>
          <Icon className={cn("h-4 w-4", variantStyles.iconColor)} />
        </div>
      </div>

      <div className="mt-4 space-y-1">
        <div className="flex items-baseline gap-2">
          <span className={cn("text-2xl font-extrabold tracking-tight font-mono", variantStyles.valColor)}>
            {value}
          </span>
          {badge && (
            <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] font-mono text-slate-300">
              {badge}
            </span>
          )}
        </div>
        {subtitle && (
          <p className="text-xs text-slate-400 font-light">{subtitle}</p>
        )}
      </div>
    </div>
  );
}
