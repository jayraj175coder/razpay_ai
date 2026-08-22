"use client";

import { useEffect, useState } from "react";
import { Header } from "@/components/layout/header";
import { KPICard } from "@/components/dashboard/kpi-card";
import { RecoveryChart } from "@/components/dashboard/recovery-chart";
import { StatusPipeline } from "@/components/dashboard/source-breakdown";
import { RecentCasesTable } from "@/components/dashboard/recent-cases-table";
import { fetchMetrics, fetchCases, triggerAiDiagnosis, LedgerMetrics, RecoveryCaseSummary } from "@/lib/api";
import { formatINR, formatPercent } from "@/lib/utils";
import {
  TrendingUp,
  ShieldCheck,
  AlertOctagon,
  Percent,
  CheckCircle2,
  Users,
  ShieldX,
  Bot,
  RefreshCw,
} from "lucide-react";

export default function DashboardPage() {
  const [metrics, setMetrics] = useState<LedgerMetrics | null>(null);
  const [cases, setCases] = useState<RecoveryCaseSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [diagnosingId, setDiagnosingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      const [m, c] = await Promise.all([
        fetchMetrics(),
        fetchCases({ limit: 10 }),
      ]);
      setMetrics(m);
      setCases(c.cases);
      setError(null);
    } catch (err: any) {
      console.error("Dashboard fetch failed:", err);
      setError("Unable to connect to RecoverAI API. Make sure the backend server is running on port 8000.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, []);

  const handleDiagnose = async (caseId: string) => {
    setDiagnosingId(caseId);
    try {
      await triggerAiDiagnosis(caseId);
      await loadDashboardData();
    } catch (err: any) {
      alert(`Diagnosis failed: ${err.message}`);
    } finally {
      setDiagnosingId(null);
    }
  };

  return (
    <div className="flex flex-col flex-1 pb-16">
      <Header title="Revenue Command Center" />

      <div className="p-8 space-y-8">
        {/* Error Alert */}
        {error && (
          <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-300 flex items-center justify-between">
            <span>{error}</span>
            <button
              onClick={loadDashboardData}
              className="rounded bg-rose-500/20 px-3 py-1 text-xs font-semibold hover:bg-rose-500/30 transition"
            >
              Retry
            </button>
          </div>
        )}

        {/* Top KPI Metrics Grid */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <KPICard
            title="Revenue at Risk"
            value={metrics ? formatINR(metrics.total_revenue_at_risk) : "₹0"}
            subtitle="Total identified payment leakages"
            icon={AlertOctagon}
            variant="crimson"
          />

          <KPICard
            title="Recoverable Revenue"
            value={metrics ? formatINR(metrics.total_recoverable_revenue) : "₹0"}
            subtitle="Probable recovery target (p >= 50%)"
            icon={ShieldCheck}
            variant="blue"
          />

          <KPICard
            title="Recovered Revenue"
            value={metrics ? formatINR(metrics.total_recovered_revenue) : "₹0"}
            subtitle="Verified captured financial ledger"
            icon={TrendingUp}
            variant="emerald"
            badge="Reconciled"
          />

          <KPICard
            title="Recovery Rate"
            value={metrics ? `${metrics.recovery_rate_pct}%` : "0%"}
            subtitle="Recovered vs Total At-Risk"
            icon={Percent}
            variant="amber"
          />
        </div>

        {/* Operational Guardrail Stats */}
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div className="rounded-lg border border-slate-800 bg-slate-900/30 p-3 text-xs">
            <span className="text-slate-400">Active Cases</span>
            <div className="mt-1 flex items-center gap-1.5 text-base font-bold font-mono text-white">
              <Users className="h-4 w-4 text-blue-400" />
              {metrics?.active_cases_count ?? 0}
            </div>
          </div>

          <div className="rounded-lg border border-slate-800 bg-slate-900/30 p-3 text-xs">
            <span className="text-slate-400">Automated Actions</span>
            <div className="mt-1 flex items-center gap-1.5 text-base font-bold font-mono text-emerald-400">
              <Bot className="h-4 w-4 text-emerald-400" />
              {metrics?.automated_actions_count ?? 0}
            </div>
          </div>

          <div className="rounded-lg border border-slate-800 bg-slate-900/30 p-3 text-xs">
            <span className="text-slate-400">Human Escalations</span>
            <div className="mt-1 flex items-center gap-1.5 text-base font-bold font-mono text-purple-400">
              <Users className="h-4 w-4 text-purple-400" />
              {metrics?.human_escalations_count ?? 0}
            </div>
          </div>

          <div className="rounded-lg border border-slate-800 bg-slate-900/30 p-3 text-xs">
            <span className="text-slate-400">Policy Blocked</span>
            <div className="mt-1 flex items-center gap-1.5 text-base font-bold font-mono text-rose-400">
              <ShieldX className="h-4 w-4 text-rose-400" />
              {metrics?.policy_blocked_actions_count ?? 0}
            </div>
          </div>
        </div>

        {/* Charts Grid */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <RecoveryChart sourceBreakdown={metrics?.source_breakdown || []} />
          </div>
          <div>
            <StatusPipeline
              statusCounts={metrics?.status_counts || {}}
              totalCases={metrics?.total_cases_count || 0}
            />
          </div>
        </div>

        {/* Live Recovery Cases Table */}
        <RecentCasesTable
          cases={cases}
          onDiagnose={handleDiagnose}
          isDiagnosing={diagnosingId}
        />
      </div>
    </div>
  );
}
