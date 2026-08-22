"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Header } from "@/components/layout/header";
import { fetchCases, triggerAiDiagnosis, RecoveryCaseSummary } from "@/lib/api";
import { formatINR, formatPercent, formatDate } from "@/lib/utils";
import {
  Search,
  Filter,
  Cpu,
  ArrowUpRight,
  ShieldAlert,
  CheckCircle2,
  Clock,
  RefreshCw,
} from "lucide-react";

export default function RecoveryQueuePage() {
  const [cases, setCases] = useState<RecoveryCaseSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [sourceFilter, setSourceFilter] = useState("ALL");
  const [riskFilter, setRiskFilter] = useState("ALL");
  const [diagnosingId, setDiagnosingId] = useState<string | null>(null);

  const loadCases = async () => {
    try {
      setLoading(true);
      const res = await fetchCases({
        status: statusFilter !== "ALL" ? statusFilter : undefined,
        source_type: sourceFilter !== "ALL" ? sourceFilter : undefined,
        risk_category: riskFilter !== "ALL" ? riskFilter : undefined,
        search: search || undefined,
        limit: 100,
      });
      setCases(res.cases);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCases();
  }, [statusFilter, sourceFilter, riskFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loadCases();
  };

  const handleDiagnose = async (caseId: string) => {
    setDiagnosingId(caseId);
    try {
      await triggerAiDiagnosis(caseId);
      await loadCases();
    } catch (err: any) {
      alert(`Diagnosis failed: ${err.message}`);
    } finally {
      setDiagnosingId(null);
    }
  };

  return (
    <div className="flex flex-col flex-1 pb-16">
      <Header title="Recovery Case Queue" />

      <div className="p-8 space-y-6">
        {/* Filter Controls Bar */}
        <div className="flex flex-col gap-4 rounded-xl border border-slate-800 bg-slate-900/40 p-4 lg:flex-row lg:items-center lg:justify-between backdrop-blur-sm">
          {/* Search */}
          <form onSubmit={handleSearchSubmit} className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search case ID or customer name..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full rounded-lg border border-slate-800 bg-slate-950/80 py-2 pl-9 pr-4 text-xs text-white placeholder-slate-400 focus:border-emerald-500 focus:outline-none"
            />
          </form>

          {/* Filters */}
          <div className="flex flex-wrap items-center gap-3">
            {/* Status */}
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="rounded-lg border border-slate-800 bg-slate-950/80 px-3 py-2 text-xs text-slate-300 focus:border-emerald-500 focus:outline-none"
            >
              <option value="ALL">All States</option>
              <option value="DETECTED">Detected</option>
              <option value="POLICY_CHECK">Policy Gate</option>
              <option value="APPROVED">Approved</option>
              <option value="EXECUTING">Executing</option>
              <option value="RETRY_SCHEDULED">Retry Scheduled</option>
              <option value="ESCALATED">Escalated</option>
              <option value="RECOVERED">Recovered</option>
              <option value="STOPPED">Stopped</option>
            </select>

            {/* Source */}
            <select
              value={sourceFilter}
              onChange={(e) => setSourceFilter(e.target.value)}
              className="rounded-lg border border-slate-800 bg-slate-950/80 px-3 py-2 text-xs text-slate-300 focus:border-emerald-500 focus:outline-none"
            >
              <option value="ALL">All Sources</option>
              <option value="PAYMENT_FAILURE">Payment Failure</option>
              <option value="SUBSCRIPTION_DUNNING">Subscription Dunning</option>
              <option value="CHECKOUT_ABANDONMENT">Checkout Abandonment</option>
              <option value="OVERDUE_INVOICE">Overdue Invoice</option>
            </select>

            {/* Risk */}
            <select
              value={riskFilter}
              onChange={(e) => setRiskFilter(e.target.value)}
              className="rounded-lg border border-slate-800 bg-slate-950/80 px-3 py-2 text-xs text-slate-300 focus:border-emerald-500 focus:outline-none"
            >
              <option value="ALL">All Risk Tiers</option>
              <option value="CRITICAL">Critical Tier</option>
              <option value="HIGH">High Tier</option>
              <option value="MEDIUM">Medium Tier</option>
              <option value="LOW">Low Tier</option>
            </select>

            <button
              onClick={loadCases}
              className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-700 hover:text-white transition"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </button>
          </div>
        </div>

        {/* Case Queue Table */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 backdrop-blur-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-900/80 text-[11px] font-semibold uppercase tracking-wider text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="py-3.5 px-6">Case Identifier</th>
                  <th className="py-3.5 px-4">Customer</th>
                  <th className="py-3.5 px-4">Amount at Risk</th>
                  <th className="py-3.5 px-4">Source Channel</th>
                  <th className="py-3.5 px-4">AI Diagnosis</th>
                  <th className="py-3.5 px-4">Recovery Prob</th>
                  <th className="py-3.5 px-4">Status</th>
                  <th className="py-3.5 px-6 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-medium text-slate-200">
                {cases.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="py-12 text-center text-xs text-slate-400">
                      No cases match current filter criteria.
                    </td>
                  </tr>
                ) : (
                  cases.map((c) => (
                    <tr key={c.id} className="hover:bg-slate-800/30 transition-colors">
                      <td className="py-3.5 px-6 font-mono font-bold text-white">
                        <Link href={`/recovery/${c.id}`} className="hover:text-emerald-400 transition">
                          {c.id}
                        </Link>
                      </td>

                      <td className="py-3.5 px-4">
                        <div className="flex flex-col">
                          <span className="font-semibold text-slate-200">{c.customer_name}</span>
                          <span className="text-[10px] text-slate-400 font-mono">{c.customer_segment}</span>
                        </div>
                      </td>

                      <td className="py-3.5 px-4 font-mono font-bold text-white text-sm">
                        {formatINR(c.amount_at_risk)}
                      </td>

                      <td className="py-3.5 px-4 font-mono text-[11px] text-slate-300">
                        {c.source_type.replace("_", " ")}
                      </td>

                      <td className="py-3.5 px-4">
                        <span className="rounded bg-slate-800 px-2 py-0.5 text-[11px] font-mono text-slate-300">
                          {c.root_cause || "Pending"}
                        </span>
                      </td>

                      <td className="py-3.5 px-4">
                        <div className="flex items-center gap-2">
                          <div className="h-1.5 w-12 overflow-hidden rounded-full bg-slate-800">
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
                          <span className="font-mono text-[11px] text-slate-300">
                            {formatPercent(c.recovery_probability, 0)}
                          </span>
                        </div>
                      </td>

                      <td className="py-3.5 px-4">
                        <span className="rounded-full bg-slate-800/80 border border-slate-700/60 px-2.5 py-0.5 text-[10px] font-mono text-slate-300">
                          {c.status}
                        </span>
                      </td>

                      <td className="py-3.5 px-6 text-right">
                        <div className="flex items-center justify-end gap-2">
                          {c.status === "DETECTED" && (
                            <button
                              onClick={() => handleDiagnose(c.id)}
                              disabled={diagnosingId === c.id}
                              className="flex items-center gap-1 rounded bg-emerald-500/20 border border-emerald-500/40 px-2.5 py-1 text-[11px] font-semibold text-emerald-300 hover:bg-emerald-500/30 transition disabled:opacity-50"
                            >
                              <Cpu className="h-3 w-3" />
                              {diagnosingId === c.id ? "Running..." : "Run AI"}
                            </button>
                          )}
                          <Link
                            href={`/recovery/${c.id}`}
                            className="rounded border border-slate-700 bg-slate-800 px-2.5 py-1 text-[11px] font-medium text-slate-300 hover:bg-slate-700 hover:text-white transition"
                          >
                            Investigate
                          </Link>
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
