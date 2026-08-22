"use client";

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
import { formatINR } from "@/lib/utils";

interface RecoveryChartProps {
  sourceBreakdown: Array<{
    source_type: string;
    amount_at_risk: number;
    recovered_amount: number;
    recovery_rate: number;
  }>;
}

export function RecoveryChart({ sourceBreakdown }: RecoveryChartProps) {
  const chartData = sourceBreakdown.map((item) => ({
    name: item.source_type
      .replace("_", " ")
      .toLowerCase()
      .replace(/\b\w/g, (l) => l.toUpperCase()),
    "At Risk": item.amount_at_risk,
    "Recovered": item.recovered_amount,
  }));

  if (!chartData || chartData.length === 0) {
    return (
      <div className="flex h-72 items-center justify-center rounded-xl border border-slate-800 bg-slate-900/30 text-xs text-slate-400">
        No transaction data recorded yet.
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5 backdrop-blur-sm">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-white">Recovery Performance by Channel</h2>
          <p className="text-xs text-slate-400">Comparing total revenue at risk vs verified recovered revenue</p>
        </div>
        <span className="rounded border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[11px] font-medium text-emerald-400">
          Live Ledger
        </span>
      </div>

      <div className="h-72 w-full">
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
            <Legend
              wrapperStyle={{ fontSize: "12px", paddingTop: "10px" }}
              iconType="circle"
            />
            <Bar dataKey="At Risk" fill="#f43f5e" radius={[4, 4, 0, 0]} maxBarSize={40} />
            <Bar dataKey="Recovered" fill="#10b981" radius={[4, 4, 0, 0]} maxBarSize={40} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
