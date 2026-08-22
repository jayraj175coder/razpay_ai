"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Header } from "@/components/layout/header";
import { fetchPendingApprovals, submitApprovalDecision } from "@/lib/api";
import { formatINR, formatDate } from "@/lib/utils";
import {
  UserCheck,
  CheckCircle2,
  XCircle,
  ShieldAlert,
  Clock,
  ArrowUpRight,
  RefreshCw,
  Sliders,
  DollarSign,
} from "lucide-react";

export default function ApprovalsPage() {
  const [pending, setPending] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);

  const loadApprovals = async () => {
    try {
      setLoading(true);
      const res = await fetchPendingApprovals();
      setPending(res.pending_approvals);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadApprovals();
  }, []);

  const handleDecision = async (caseId: string, decision: "APPROVE" | "REJECT") => {
    setActionLoading(caseId);
    try {
      const res = await submitApprovalDecision(
        caseId,
        decision,
        "operator_lead",
        decision === "APPROVE" ? "Approved by operations officer" : "Rejected by operations officer"
      );
      setFeedback(`Case ${caseId} marked as ${res.status}!`);
      await loadApprovals();
    } catch (err: any) {
      alert(`Decision failed: ${err.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  const totalAtRiskInQueue = pending.reduce((sum, p) => sum + p.amount_at_risk, 0);

  return (
    <div className="flex flex-col flex-1 pb-16">
      <Header title="Human Recovery Approvals" />

      <div className="p-8 space-y-6 max-w-7xl">
        {/* Banner Alert */}
        <div className="rounded-xl border border-purple-500/30 bg-purple-500/10 p-5 backdrop-blur-sm flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-purple-500/20 text-purple-400">
              <UserCheck className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-white">Human-in-the-Loop Governance Queue</h2>
              <p className="text-xs text-purple-300/80">
                Transactions exceeding ₹1,00,000 threshold or requiring manual risk intervention before execution.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4 text-right">
            <div>
              <span className="text-[10px] font-mono uppercase text-slate-400 block">Pending Queue Value</span>
              <span className="text-xl font-bold font-mono text-white">{formatINR(totalAtRiskInQueue)}</span>
            </div>
            <div className="rounded-lg bg-purple-500/20 px-3 py-1.5 text-center font-mono font-bold text-purple-300 text-sm">
              {pending.length} Cases
            </div>
          </div>
        </div>

        {feedback && (
          <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3 text-xs font-medium text-emerald-300 flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4" />
            {feedback}
          </div>
        )}

        {/* Approvals Table */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 backdrop-blur-sm overflow-hidden">
          <div className="flex items-center justify-between border-b border-slate-800 px-6 py-4">
            <div>
              <h3 className="text-sm font-bold text-white">Escalated Case Queue</h3>
              <p className="text-xs text-slate-400">Review AI recommendations and policy gate triggers</p>
            </div>
            <button
              onClick={loadApprovals}
              className="flex items-center gap-1 text-xs text-slate-400 hover:text-white"
            >
              <RefreshCw className={`h-3 w-3 ${loading ? "animate-spin" : ""}`} /> Refresh
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-900/80 text-[11px] font-semibold uppercase tracking-wider text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="py-3.5 px-6">Case & Customer</th>
                  <th className="py-3.5 px-4">Amount at Risk</th>
                  <th className="py-3.5 px-4">Customer LTV</th>
                  <th className="py-3.5 px-4">Proposed Strategy</th>
                  <th className="py-3.5 px-4">Policy Reason</th>
                  <th className="py-3.5 px-6 text-right">Decision Controls</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-medium text-slate-200">
                {pending.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-12 text-center text-xs text-slate-400">
                      <CheckCircle2 className="h-6 w-6 text-emerald-400 mx-auto mb-2 opacity-60" />
                      All approval queues cleared! No cases pending sign-off.
                    </td>
                  </tr>
                ) : (
                  pending.map((item) => (
                    <tr key={item.case_id} className="hover:bg-slate-800/30">
                      <td className="py-4 px-6">
                        <div className="flex flex-col">
                          <Link
                            href={`/recovery/${item.case_id}`}
                            className="font-mono font-bold text-white hover:text-emerald-400 transition"
                          >
                            {item.case_id}
                          </Link>
                          <span className="font-semibold text-slate-200 mt-0.5">{item.customer_name}</span>
                          <span className="text-[10px] text-slate-400 font-mono">{item.customer_segment}</span>
                        </div>
                      </td>

                      <td className="py-4 px-4 font-mono font-bold text-white text-base">
                        {formatINR(item.amount_at_risk)}
                      </td>

                      <td className="py-4 px-4 font-mono text-slate-300 text-xs">
                        {formatINR(item.customer_ltv)}
                      </td>

                      <td className="py-4 px-4">
                        <div className="flex flex-col gap-0.5">
                          <span className="font-mono font-semibold text-white text-[11px]">
                            {item.recommended_action}
                          </span>
                          <span className="text-[10px] text-emerald-400 font-mono">
                            Channel: {item.recommended_channel}
                          </span>
                        </div>
                      </td>

                      <td className="py-4 px-4 max-w-xs">
                        <span className="text-[11px] text-amber-300/90 leading-tight block">
                          {item.policy_reason}
                        </span>
                      </td>

                      <td className="py-4 px-6 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <Link
                            href={`/recovery/${item.case_id}`}
                            className="rounded border border-slate-700 bg-slate-800 px-2.5 py-1 text-[11px] font-medium text-slate-300 hover:bg-slate-700 hover:text-white transition"
                          >
                            Details
                          </Link>
                          <button
                            disabled={actionLoading === item.case_id}
                            onClick={() => handleDecision(item.case_id, "REJECT")}
                            className="flex items-center gap-1 rounded border border-rose-500/30 bg-rose-500/10 px-2.5 py-1 text-[11px] font-semibold text-rose-300 hover:bg-rose-500/20 transition disabled:opacity-50"
                          >
                            <XCircle className="h-3 w-3" />
                            Reject
                          </button>
                          <button
                            disabled={actionLoading === item.case_id}
                            onClick={() => handleDecision(item.case_id, "APPROVE")}
                            className="flex items-center gap-1 rounded bg-emerald-500 px-3 py-1 text-[11px] font-bold text-slate-950 hover:bg-emerald-400 transition disabled:opacity-50 shadow-sm"
                          >
                            <CheckCircle2 className="h-3 w-3" />
                            {actionLoading === item.case_id ? "Executing..." : "Approve & Collect"}
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
