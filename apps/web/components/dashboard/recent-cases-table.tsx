"use client";

import Link from "next/link";
import { formatINR, formatPercent, formatDate } from "@/lib/utils";
import { RecoveryCaseSummary } from "@/lib/api";
import { ArrowUpRight, Cpu, ShieldAlert, CheckCircle2, Clock } from "lucide-react";

interface RecentCasesTableProps {
  cases: RecoveryCaseSummary[];
  onDiagnose?: (caseId: string) => void;
  isDiagnosing?: string | null;
}

export function RecentCasesTable({ cases, onDiagnose, isDiagnosing }: RecentCasesTableProps) {
  const getStatusBadge = (status: string) => {
    switch (status) {
      case "RECOVERED":
        return <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 text-[11px] font-medium text-emerald-400"><CheckCircle2 className="h-3 w-3" /> Recovered</span>;
      case "ESCALATED":
        return <span className="inline-flex items-center gap-1 rounded-full bg-purple-500/10 border border-purple-500/20 px-2 py-0.5 text-[11px] font-medium text-purple-400"><ShieldAlert className="h-3 w-3" /> Escalated</span>;
      case "POLICY_CHECK":
        return <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 text-[11px] font-medium text-amber-300"><Clock className="h-3 w-3" /> Policy Gate</span>;
      case "RETRY_SCHEDULED":
      case "EXECUTING":
        return <span className="inline-flex items-center gap-1 rounded-full bg-blue-500/10 border border-blue-500/20 px-2 py-0.5 text-[11px] font-medium text-blue-300"><Clock className="h-3 w-3" /> Retrying</span>;
      default:
        return <span className="inline-flex items-center rounded-full bg-slate-800 px-2 py-0.5 text-[11px] font-medium text-slate-300">{status}</span>;
    }
  };

  const getRiskBadge = (category: string) => {
    switch (category) {
      case "CRITICAL":
        return <span className="rounded bg-rose-500/10 text-rose-400 border border-rose-500/20 px-1.5 py-0.5 text-[10px] font-semibold">CRITICAL</span>;
      case "HIGH":
        return <span className="rounded bg-amber-500/10 text-amber-400 border border-amber-500/20 px-1.5 py-0.5 text-[10px] font-semibold">HIGH</span>;
      case "MEDIUM":
        return <span className="rounded bg-blue-500/10 text-blue-400 border border-blue-500/20 px-1.5 py-0.5 text-[10px] font-semibold">MEDIUM</span>;
      default:
        return <span className="rounded bg-slate-800 text-slate-400 px-1.5 py-0.5 text-[10px] font-semibold">LOW</span>;
    }
  };

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/40 backdrop-blur-sm overflow-hidden">
      <div className="flex items-center justify-between border-b border-slate-800 px-6 py-4">
        <div>
          <h2 className="text-sm font-semibold text-white">Active Recovery Stream</h2>
          <p className="text-xs text-slate-400">Real-time revenue risk detections and intervention statuses</p>
        </div>
        <Link
          href="/recovery"
          className="flex items-center gap-1 text-xs font-semibold text-emerald-400 hover:text-emerald-300 transition"
        >
          View all cases <ArrowUpRight className="h-3.5 w-3.5" />
        </Link>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-900/80 text-[11px] font-semibold uppercase tracking-wider text-slate-400 border-b border-slate-800">
            <tr>
              <th className="py-3 px-6">Case ID & Customer</th>
              <th className="py-3 px-4">Amount at Risk</th>
              <th className="py-3 px-4">Channel / Cause</th>
              <th className="py-3 px-4">Recovery Probability</th>
              <th className="py-3 px-4">Status</th>
              <th className="py-3 px-6 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 font-medium text-slate-200">
            {cases.map((c) => (
              <tr key={c.id} className="hover:bg-slate-800/30 transition-colors">
                <td className="py-3.5 px-6">
                  <div className="flex flex-col">
                    <Link href={`/recovery/${c.id}`} className="font-mono font-bold text-white hover:text-emerald-400 transition">
                      {c.id}
                    </Link>
                    <span className="text-[11px] text-slate-400 flex items-center gap-1.5 mt-0.5">
                      {c.customer_name} • <span className="text-slate-400">{c.customer_segment}</span>
                    </span>
                  </div>
                </td>

                <td className="py-3.5 px-4">
                  <span className="font-mono font-bold text-white text-sm">
                    {formatINR(c.amount_at_risk)}
                  </span>
                  {c.recovered_amount > 0 && (
                    <span className="block text-[10px] font-mono text-emerald-400">
                      Recovered: {formatINR(c.recovered_amount)}
                    </span>
                  )}
                </td>

                <td className="py-3.5 px-4">
                  <div className="flex flex-col gap-1">
                    <span className="text-[11px] text-slate-300 font-mono">
                      {c.source_type.replace("_", " ")}
                    </span>
                    <span className="text-[10px] text-slate-400">
                      {c.root_cause || "Analyzing..."}
                    </span>
                  </div>
                </td>

                <td className="py-3.5 px-4">
                  <div className="flex items-center gap-2">
                    <div className="h-1.5 w-14 overflow-hidden rounded-full bg-slate-800">
                      <div
                        className={`h-full ${
                          c.recovery_probability >= 0.8
                            ? "bg-emerald-500"
                            : c.recovery_probability >= 0.5
                            ? "bg-amber-500"
                            : "bg-rose-500"
                        }`}
                        style={{ width: `${c.recovery_probability * 100}%` }}
                      />
                    </div>
                    <span className="font-mono text-xs text-slate-300">
                      {formatPercent(c.recovery_probability, 0)}
                    </span>
                    {getRiskBadge(c.risk_category)}
                  </div>
                </td>

                <td className="py-3.5 px-4">
                  {getStatusBadge(c.status)}
                </td>

                <td className="py-3.5 px-6 text-right">
                  <div className="flex items-center justify-end gap-2">
                    {c.status === "DETECTED" && onDiagnose && (
                      <button
                        onClick={() => onDiagnose(c.id)}
                        disabled={isDiagnosing === c.id}
                        className="flex items-center gap-1 rounded bg-emerald-500/20 border border-emerald-500/40 px-2.5 py-1 text-[11px] font-semibold text-emerald-300 hover:bg-emerald-500/30 transition disabled:opacity-50"
                      >
                        <Cpu className="h-3 w-3" />
                        {isDiagnosing === c.id ? "Diagnosing..." : "Run AI"}
                      </button>
                    )}
                    <Link
                      href={`/recovery/${c.id}`}
                      className="rounded border border-slate-700 bg-slate-800/80 px-2.5 py-1 text-[11px] font-medium text-slate-300 hover:bg-slate-700 hover:text-white transition"
                    >
                      Investigate
                    </Link>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
