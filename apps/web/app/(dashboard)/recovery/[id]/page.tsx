"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { Header } from "@/components/layout/header";
import { fetchCaseDetail, triggerAiDiagnosis, approveCase, rejectCase, CaseDetail } from "@/lib/api";
import { formatINR, formatPercent, formatDate } from "@/lib/utils";
import {
  ArrowLeft,
  Cpu,
  ShieldCheck,
  ShieldAlert,
  CheckCircle2,
  XCircle,
  Clock,
  User,
  Activity,
  CreditCard,
  Send,
  MessageSquare,
  AlertTriangle,
  History,
  FileText,
} from "lucide-react";

export default function CaseInvestigationPage() {
  const params = useParams();
  const router = useRouter();
  const caseId = params.id as string;

  const [caseData, setCaseData] = useState<CaseDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);

  const loadCase = async () => {
    try {
      setLoading(true);
      const data = await fetchCaseDetail(caseId);
      setCaseData(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (caseId) loadCase();
  }, [caseId]);

  const handleRunAi = async () => {
    setActionLoading(true);
    try {
      await triggerAiDiagnosis(caseId);
      setFeedback("AI Diagnosis & Strategy generated successfully.");
      await loadCase();
    } catch (err: any) {
      alert(`AI run failed: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleApprove = async () => {
    setActionLoading(true);
    try {
      const res = await approveCase(caseId, "Approved by operator in investigation view");
      setFeedback(`Case approved! Recovered: ${formatINR(res.recovered_amount)}`);
      await loadCase();
    } catch (err: any) {
      alert(`Approval failed: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async () => {
    setActionLoading(true);
    try {
      await rejectCase(caseId, "Rejected by operator in investigation view");
      setFeedback("Case marked as STOPPED.");
      await loadCase();
    } catch (err: any) {
      alert(`Rejection failed: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  if (loading || !caseData) {
    return (
      <div className="flex flex-col flex-1 pb-16">
        <Header title="Case Investigation" />
        <div className="flex h-96 items-center justify-center text-xs text-slate-400">
          Loading case data...
        </div>
      </div>
    );
  }

  const isEscalated = caseData.status === "ESCALATED" || caseData.status === "POLICY_CHECK";
  const isRecovered = caseData.status === "RECOVERED";

  return (
    <div className="flex flex-col flex-1 pb-16">
      <Header title={`Investigation: ${caseData.id}`} />

      <div className="p-8 space-y-6 max-w-7xl">
        {/* Back Link & Title Header */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-slate-800 pb-6">
          <div className="flex items-center gap-3">
            <Link
              href="/recovery"
              className="rounded-lg border border-slate-800 bg-slate-900/80 p-2 text-slate-400 hover:text-white transition"
            >
              <ArrowLeft className="h-4 w-4" />
            </Link>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-xl font-extrabold text-white">{caseData.id}</span>
                <span className="rounded-full bg-slate-800 border border-slate-700 px-2.5 py-0.5 text-xs font-mono text-slate-300">
                  {caseData.status}
                </span>
                {isRecovered && (
                  <span className="rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 px-2.5 py-0.5 text-xs font-semibold flex items-center gap-1">
                    <CheckCircle2 className="h-3.5 w-3.5" /> Reconciled
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400 mt-1 font-mono">
                Source: {caseData.source_type} • Created: {formatDate(caseData.created_at)}
              </p>
            </div>
          </div>

          {/* Action Bar */}
          <div className="flex items-center gap-3">
            {caseData.status === "DETECTED" && (
              <button
                disabled={actionLoading}
                onClick={handleRunAi}
                className="flex items-center gap-1.5 rounded-lg bg-emerald-500 px-4 py-2 text-xs font-semibold text-slate-950 hover:bg-emerald-400 transition disabled:opacity-50 shadow-md shadow-emerald-500/20"
              >
                <Cpu className="h-3.5 w-3.5" />
                {actionLoading ? "Processing..." : "Run AI Diagnosis"}
              </button>
            )}

            {isEscalated && (
              <>
                <button
                  disabled={actionLoading}
                  onClick={handleReject}
                  className="flex items-center gap-1.5 rounded-lg border border-rose-500/30 bg-rose-500/10 px-3.5 py-2 text-xs font-semibold text-rose-300 hover:bg-rose-500/20 transition disabled:opacity-50"
                >
                  <XCircle className="h-3.5 w-3.5" />
                  Reject & Stop
                </button>
                <button
                  disabled={actionLoading}
                  onClick={handleApprove}
                  className="flex items-center gap-1.5 rounded-lg bg-emerald-500 px-4 py-2 text-xs font-semibold text-slate-950 hover:bg-emerald-400 transition disabled:opacity-50 shadow-md shadow-emerald-500/20"
                >
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  Approve Recovery Action
                </button>
              </>
            )}
          </div>
        </div>

        {feedback && (
          <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3 text-xs font-medium text-emerald-300 flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4" />
            {feedback}
          </div>
        )}

        {/* Top Overview Cards */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {/* Amount at Risk */}
          <div className="rounded-xl border border-rose-500/20 bg-rose-500/[0.03] p-5 backdrop-blur-sm">
            <span className="text-xs uppercase tracking-wider text-slate-400 font-medium">Amount at Risk</span>
            <div className="mt-2 font-mono text-3xl font-extrabold text-rose-400">
              {formatINR(caseData.amount_at_risk)}
            </div>
            {caseData.recovered_amount > 0 && (
              <span className="text-xs font-mono text-emerald-400 mt-1 block">
                Recovered: {formatINR(caseData.recovered_amount)} (100%)
              </span>
            )}
          </div>

          {/* Recovery Probability */}
          <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5 backdrop-blur-sm">
            <span className="text-xs uppercase tracking-wider text-slate-400 font-medium">Recovery Probability</span>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="font-mono text-3xl font-extrabold text-white">
                {formatPercent(caseData.recovery_probability, 1)}
              </span>
              <span className="text-xs font-mono text-slate-400">
                Priority: {caseData.priority_score.toFixed(1)}/100
              </span>
            </div>
            <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
              <div
                className="h-full bg-emerald-500"
                style={{ width: `${caseData.recovery_probability * 100}%` }}
              />
            </div>
          </div>

          {/* Customer Profile Card */}
          <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5 backdrop-blur-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs uppercase tracking-wider text-slate-400 font-medium">Customer Profile</span>
              <span className="rounded bg-blue-500/10 text-blue-300 border border-blue-500/20 px-2 py-0.5 text-[10px] font-semibold">
                {caseData.customer?.segment || "RETAIL"}
              </span>
            </div>
            <div className="mt-2">
              <span className="font-bold text-white text-base block">{caseData.customer?.name}</span>
              <span className="text-xs text-slate-400 font-mono block">{caseData.customer?.email}</span>
              <span className="text-[11px] text-slate-400 font-mono mt-1 block">
                Historical LTV: {formatINR(caseData.customer?.lifetime_value || 0)}
              </span>
            </div>
          </div>
        </div>

        {/* AI Diagnosis & Strategy Section */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* AI Root-Cause Reasoning Card */}
          <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-6 backdrop-blur-sm space-y-4">
            <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
              <Cpu className="h-5 w-5 text-emerald-400" />
              <h2 className="text-sm font-bold text-white">AI Root-Cause Diagnosis</h2>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <span className="text-slate-400 block text-[11px] uppercase font-mono">Diagnosed Cause:</span>
                <span className="font-mono font-bold text-emerald-300 text-sm">
                  {caseData.root_cause || "Pending AI analysis"}
                </span>
              </div>

              <div>
                <span className="text-slate-400 block text-[11px] uppercase font-mono">Explanation:</span>
                <p className="text-slate-200 mt-1 leading-relaxed bg-slate-950/60 p-3 rounded-lg border border-slate-800 font-sans">
                  {caseData.root_cause_explanation || "No explanation generated yet. Click 'Run AI Diagnosis' to analyze."}
                </p>
              </div>

              {/* Signals Breakdown */}
              <div className="pt-2">
                <span className="text-slate-400 block text-[11px] uppercase font-mono mb-2">Explainable Signals:</span>
                <div className="space-y-1.5">
                  {caseData.signals?.positive?.map((sig, i) => (
                    <div key={i} className="flex items-center gap-2 text-emerald-400 bg-emerald-500/5 px-2.5 py-1.5 rounded border border-emerald-500/10">
                      <CheckCircle2 className="h-3.5 w-3.5 shrink-0" />
                      <span>{sig}</span>
                    </div>
                  ))}
                  {caseData.signals?.negative?.map((sig, i) => (
                    <div key={i} className="flex items-center gap-2 text-rose-400 bg-rose-500/5 px-2.5 py-1.5 rounded border border-rose-500/10">
                      <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
                      <span>{sig}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Policy Gate & Recommended Action */}
          <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-6 backdrop-blur-sm space-y-4">
            <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
              <ShieldCheck className="h-5 w-5 text-blue-400" />
              <h2 className="text-sm font-bold text-white">Bounded Policy & Recommended Strategy</h2>
            </div>

            <div className="space-y-3 text-xs">
              <div className="flex items-center justify-between bg-slate-950/60 p-3 rounded-lg border border-slate-800">
                <div>
                  <span className="text-slate-400 block text-[10px] uppercase font-mono">Recommended Action:</span>
                  <span className="font-mono font-bold text-white text-sm">
                    {caseData.recommended_action || "None selected"}
                  </span>
                </div>
                <div className="text-right">
                  <span className="text-slate-400 block text-[10px] uppercase font-mono">Channel:</span>
                  <span className="font-mono text-emerald-400 font-semibold">
                    {caseData.recommended_channel || "SMART_RETRY"}
                  </span>
                </div>
              </div>

              <div>
                <span className="text-slate-400 block text-[11px] uppercase font-mono">Strategy Rationale:</span>
                <p className="text-slate-300 mt-1 leading-relaxed bg-slate-950/60 p-3 rounded-lg border border-slate-800">
                  {caseData.ai_reasoning || "Pending strategy synthesis."}
                </p>
              </div>

              {/* Latest Policy Decision */}
              {caseData.actions.length > 0 && (
                <div>
                  <span className="text-slate-400 block text-[11px] uppercase font-mono mb-1">Policy Gate Decision:</span>
                  <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800 flex flex-col gap-1">
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono ${
                        caseData.actions[0].policy_decision === "ALLOWED"
                          ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                          : caseData.actions[0].policy_decision === "BLOCKED"
                          ? "bg-rose-500/20 text-rose-400 border border-rose-500/30"
                          : "bg-purple-500/20 text-purple-300 border border-purple-500/30"
                      }`}>
                        {caseData.actions[0].policy_decision}
                      </span>
                    </div>
                    <span className="text-slate-300 mt-1 text-xs">
                      {caseData.actions[0].policy_reason}
                    </span>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Audit Log Timeline */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-6 backdrop-blur-sm space-y-4">
          <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
            <History className="h-5 w-5 text-amber-400" />
            <h2 className="text-sm font-bold text-white">Immutable Audit Trail</h2>
          </div>

          <div className="space-y-3">
            {caseData.audit_logs.length === 0 ? (
              <p className="text-xs text-slate-400">No audit events recorded yet.</p>
            ) : (
              caseData.audit_logs.map((log) => (
                <div key={log.id} className="flex items-start gap-3 rounded-lg border border-slate-800/80 bg-slate-950/50 p-3 text-xs">
                  <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-slate-800 text-slate-300">
                    <FileText className="h-3.5 w-3.5" />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <span className="font-mono font-bold text-white text-[12px]">{log.action}</span>
                      <span className="font-mono text-[10px] text-slate-400">{formatDate(log.created_at)}</span>
                    </div>
                    <p className="text-slate-300 mt-1">{log.reason}</p>
                    <span className="text-[10px] font-mono text-slate-400 mt-1 inline-block">
                      Actor: {log.actor_type} {log.actor_id ? `(${log.actor_id})` : ""}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
