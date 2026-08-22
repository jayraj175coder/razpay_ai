"use client";

import { useState, useEffect } from "react";
import { Header } from "@/components/layout/header";
import { runSimulation } from "@/lib/api";
import { formatINR, formatPercent } from "@/lib/utils";
import {
  Sliders,
  TrendingUp,
  Cpu,
  ShieldAlert,
  Play,
  CheckCircle2,
  XCircle,
  BarChart3,
  Flame,
  ArrowRight,
  ShieldCheck,
  Bot,
} from "lucide-react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
} from "recharts";

export default function SimulationPage() {
  const [count, setCount] = useState<number>(100);
  const [seed, setSeed] = useState<number>(42);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any | null>(null);

  const handleRun = async () => {
    setLoading(true);
    try {
      const data = await runSimulation(count, seed);
      setResult(data);
    } catch (err: any) {
      alert(`Simulation failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    handleRun();
  }, []);

  const chartData = (result?.breakdown_by_category || []).map((item: any) => ({
    name: item.failure_code
      .replace("_", " ")
      .toLowerCase()
      .replace(/\b\w/g, (l: string) => l.toUpperCase()),
    "Baseline Recovery": item.baseline_recovered,
    "RecoverAI Recovery": item.recoverai_recovered,
  }));

  return (
    <div className="flex flex-col flex-1 pb-16">
      <Header title="Recovery Simulation Benchmark" />

      <div className="p-8 space-y-6 max-w-7xl">
        {/* Controls Bar */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5 backdrop-blur-sm">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <h2 className="text-sm font-bold text-white flex items-center gap-2">
                <Sliders className="h-4 w-4 text-emerald-400" />
                Deterministic Synthetic Experiment Controls
              </h2>
              <p className="text-xs text-slate-400">
                Run side-by-side benchmark of Baseline static rules vs RecoverAI bounded agent on identical transactions.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              {/* Count options */}
              <div className="flex rounded-lg border border-slate-800 bg-slate-950 p-1">
                {[100, 500, 1000].map((n) => (
                  <button
                    key={n}
                    onClick={() => setCount(n)}
                    className={`rounded px-3 py-1 text-xs font-mono font-semibold transition ${
                      count === n
                        ? "bg-emerald-500 text-slate-950 shadow"
                        : "text-slate-400 hover:text-white"
                    }`}
                  >
                    {n} Cases
                  </button>
                ))}
              </div>

              {/* Seed */}
              <div className="flex items-center gap-1.5 rounded-lg border border-slate-800 bg-slate-950 px-3 py-1 text-xs">
                <span className="text-slate-400 font-mono text-[11px]">Seed:</span>
                <input
                  type="number"
                  value={seed}
                  onChange={(e) => setSeed(parseInt(e.target.value) || 1)}
                  className="w-14 bg-transparent font-mono text-white focus:outline-none"
                />
              </div>

              {/* Run Button */}
              <button
                disabled={loading}
                onClick={handleRun}
                className="flex items-center gap-2 rounded-lg bg-emerald-500 px-5 py-2 text-xs font-bold text-slate-950 hover:bg-emerald-400 transition disabled:opacity-50 shadow-lg shadow-emerald-500/20"
              >
                <Play className={`h-3.5 w-3.5 fill-current ${loading ? "animate-spin" : ""}`} />
                {loading ? "Simulating..." : "Run Benchmark"}
              </button>
            </div>
          </div>
        </div>

        {result && (
          <>
            {/* Incremental ROI Highlight Banner */}
            <div className="rounded-xl border border-emerald-500/30 bg-gradient-to-r from-emerald-950/40 via-slate-900/60 to-slate-900/40 p-6 backdrop-blur-sm flex flex-col md:flex-row items-center justify-between gap-6">
              <div className="space-y-1 text-center md:text-left">
                <div className="flex items-center gap-2 justify-center md:justify-start">
                  <Flame className="h-5 w-5 text-emerald-400" />
                  <span className="text-xs font-bold uppercase tracking-wider text-emerald-400">
                    Incremental Value Delivered
                  </span>
                </div>
                <h3 className="text-3xl font-extrabold font-mono text-white">
                  +{formatINR(result.incremental_recovered_revenue)}
                </h3>
                <p className="text-xs text-slate-400">
                  Additional revenue recovered by RecoverAI over baseline rules on {result.dataset_size} transactions.
                </p>
              </div>

              <div className="flex items-center gap-8 border-t border-slate-800 md:border-t-0 md:border-l md:pl-8 pt-4 md:pt-0">
                <div>
                  <span className="text-[11px] font-mono text-slate-400 block">Baseline Recovery</span>
                  <span className="text-xl font-bold font-mono text-slate-300">
                    {result.baseline_recovery_rate_pct}%
                  </span>
                  <span className="text-[10px] font-mono text-slate-400 block">
                    {formatINR(result.baseline_recovered_revenue)}
                  </span>
                </div>

                <ArrowRight className="h-5 w-5 text-slate-400" />

                <div>
                  <span className="text-[11px] font-mono text-emerald-400 block">RecoverAI Rate</span>
                  <span className="text-xl font-bold font-mono text-emerald-400">
                    {result.recoverai_recovery_rate_pct}%
                  </span>
                  <span className="text-[10px] font-mono text-emerald-400/80 block">
                    {formatINR(result.recoverai_recovered_revenue)}
                  </span>
                </div>

                <div className="rounded-lg bg-emerald-500/10 border border-emerald-500/20 px-3 py-2 text-center">
                  <span className="text-[10px] font-bold text-emerald-400 uppercase block">Lift</span>
                  <span className="text-lg font-extrabold font-mono text-emerald-300">
                    +{result.incremental_recovery_rate_pct.toFixed(1)}%
                  </span>
                </div>
              </div>
            </div>

            {/* Operational Guardrail Counters */}
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
                <span className="text-xs text-slate-400">Total at Risk</span>
                <div className="mt-1 font-mono text-xl font-bold text-white">
                  {formatINR(result.total_revenue_at_risk)}
                </div>
              </div>

              <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
                <span className="text-xs text-slate-400">Automated Actions</span>
                <div className="mt-1 font-mono text-xl font-bold text-emerald-400 flex items-center gap-1.5">
                  <Bot className="h-4 w-4" />
                  {result.automated_interventions_count}
                </div>
              </div>

              <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
                <span className="text-xs text-slate-400">Human Escalations</span>
                <div className="mt-1 font-mono text-xl font-bold text-purple-400">
                  {result.human_escalations_count}
                </div>
              </div>

              <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
                <span className="text-xs text-slate-400">Policy Blocks (Fraud)</span>
                <div className="mt-1 font-mono text-xl font-bold text-rose-400 flex items-center gap-1.5">
                  <ShieldCheck className="h-4 w-4" />
                  {result.policy_blocked_count}
                </div>
              </div>
            </div>

            {/* Comparative Chart */}
            <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-6 backdrop-blur-sm">
              <div className="mb-4">
                <h3 className="text-sm font-bold text-white">Category Recovery Comparison</h3>
                <p className="text-xs text-slate-400">Recovered revenue by failure taxonomy under both strategies</p>
              </div>

              <div className="h-80 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData} margin={{ top: 10, right: 10, left: 10, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                    <XAxis
                      dataKey="name"
                      stroke="#64748b"
                      fontSize={11}
                      tickLine={false}
                      axisLine={{ stroke: "#334155" }}
                    />
                    <YAxis
                      stroke="#64748b"
                      fontSize={11}
                      tickLine={false}
                      axisLine={{ stroke: "#334155" }}
                      tickFormatter={(val) => `₹${val >= 1000 ? `${(val / 1000).toFixed(0)}k` : val}`}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#0f172a",
                        borderColor: "#334155",
                        borderRadius: "0.5rem",
                        fontSize: "12px",
                        color: "#f8fafc",
                      }}
                      formatter={(val: number) => [formatINR(val), ""]}
                    />
                    <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "10px" }} />
                    <Bar dataKey="Baseline Recovery" fill="#64748b" radius={[4, 4, 0, 0]} maxBarSize={35} />
                    <Bar dataKey="RecoverAI Recovery" fill="#10b981" radius={[4, 4, 0, 0]} maxBarSize={35} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Category Breakdown Table */}
            <div className="rounded-xl border border-slate-800 bg-slate-900/40 backdrop-blur-sm overflow-hidden">
              <div className="border-b border-slate-800 px-6 py-4">
                <h3 className="text-sm font-bold text-white">Failure Code Breakdown</h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-900/80 text-[11px] font-semibold uppercase tracking-wider text-slate-400 border-b border-slate-800">
                    <tr>
                      <th className="py-3 px-6">Failure Code</th>
                      <th className="py-3 px-4">Count</th>
                      <th className="py-3 px-4">At Risk</th>
                      <th className="py-3 px-4">Baseline Rec</th>
                      <th className="py-3 px-4">RecoverAI Rec</th>
                      <th className="py-3 px-4">Delta (\u0394)</th>
                      <th className="py-3 px-6 text-right">RecoverAI %</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 font-medium text-slate-200">
                    {result.breakdown_by_category.map((cat: any) => (
                      <tr key={cat.failure_code} className="hover:bg-slate-800/30">
                        <td className="py-3 px-6 font-mono font-bold text-white">{cat.failure_code}</td>
                        <td className="py-3 px-4 font-mono text-slate-400">{cat.case_count}</td>
                        <td className="py-3 px-4 font-mono text-slate-300">{formatINR(cat.amount_at_risk)}</td>
                        <td className="py-3 px-4 font-mono text-slate-400">{formatINR(cat.baseline_recovered)} ({cat.baseline_rate}%)</td>
                        <td className="py-3 px-4 font-mono text-emerald-400 font-bold">{formatINR(cat.recoverai_recovered)}</td>
                        <td className="py-3 px-4 font-mono text-emerald-300">+{formatINR(cat.incremental_recovered)}</td>
                        <td className="py-3 px-6 text-right font-mono text-emerald-400 font-bold">{cat.recoverai_rate}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Sample Individual Cases Table */}
            <div className="rounded-xl border border-slate-800 bg-slate-900/40 backdrop-blur-sm overflow-hidden">
              <div className="border-b border-slate-800 px-6 py-4">
                <h3 className="text-sm font-bold text-white">Sample Simulated Transactions</h3>
                <p className="text-xs text-slate-400">Comparing individual transaction outcomes</p>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-900/80 text-[11px] font-semibold uppercase tracking-wider text-slate-400 border-b border-slate-800">
                    <tr>
                      <th className="py-3 px-6">Txn ID</th>
                      <th className="py-3 px-4">Customer</th>
                      <th className="py-3 px-4">Amount</th>
                      <th className="py-3 px-4">Failure Code</th>
                      <th className="py-3 px-4">Baseline</th>
                      <th className="py-3 px-4">RecoverAI</th>
                      <th className="py-3 px-6 text-right">Action Taken</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 font-medium text-slate-200">
                    {result.sample_cases.map((sc: any) => (
                      <tr key={sc.id} className="hover:bg-slate-800/30">
                        <td className="py-3 px-6 font-mono font-bold text-white">{sc.id}</td>
                        <td className="py-3 px-4">{sc.customer_name}</td>
                        <td className="py-3 px-4 font-mono font-bold">{formatINR(sc.amount)}</td>
                        <td className="py-3 px-4 font-mono text-[11px] text-slate-300">{sc.failure_code}</td>
                        <td className="py-3 px-4">
                          {sc.baseline_recovered ? (
                            <span className="text-emerald-400 flex items-center gap-1 font-semibold"><CheckCircle2 className="h-3.5 w-3.5" /> Recovered</span>
                          ) : (
                            <span className="text-slate-400 flex items-center gap-1"><XCircle className="h-3.5 w-3.5" /> Failed</span>
                          )}
                        </td>
                        <td className="py-3 px-4">
                          {sc.recoverai_recovered ? (
                            <span className="text-emerald-400 flex items-center gap-1 font-bold"><CheckCircle2 className="h-3.5 w-3.5" /> Recovered</span>
                          ) : (
                            <span className="text-rose-400 flex items-center gap-1 font-semibold"><XCircle className="h-3.5 w-3.5" /> Blocked/Failed</span>
                          )}
                        </td>
                        <td className="py-3 px-6 text-right font-mono text-[11px] text-slate-300">
                          {sc.action_taken}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
