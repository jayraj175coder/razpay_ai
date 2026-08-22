import { formatINR, formatPercent } from "@/lib/utils";
import { CheckCircle, AlertTriangle, Clock, RefreshCw } from "lucide-react";

interface StatusPipelineProps {
  statusCounts: Record<string, number>;
  totalCases: number;
}

export function StatusPipeline({ statusCounts, totalCases }: StatusPipelineProps) {
  const recovered = statusCounts["RECOVERED"] || 0;
  const awaiting = (statusCounts["EXECUTING"] || 0) + (statusCounts["AWAITING_RESULT"] || 0);
  const escalated = statusCounts["ESCALATED"] || 0;
  const policyCheck = (statusCounts["POLICY_CHECK"] || 0) + (statusCounts["ACTION_PROPOSED"] || 0) + (statusCounts["DETECTED"] || 0);

  const stages = [
    { label: "Detected & Policy Check", count: policyCheck, color: "bg-blue-500", text: "text-blue-400", icon: Clock },
    { label: "Executing & Awaiting", count: awaiting, color: "bg-amber-500", text: "text-amber-400", icon: RefreshCw },
    { label: "Human Escalated", count: escalated, color: "bg-purple-500", text: "text-purple-400", icon: AlertTriangle },
    { label: "Verified Recovered", count: recovered, color: "bg-emerald-500", text: "text-emerald-400", icon: CheckCircle },
  ];

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5 backdrop-blur-sm">
      <div className="mb-4">
        <h2 className="text-sm font-semibold text-white">Recovery Case Lifecycle Distribution</h2>
        <p className="text-xs text-slate-400">Cases progressing through the state machine</p>
      </div>

      {/* Progress Bar Stack */}
      <div className="flex h-3 w-full overflow-hidden rounded-full bg-slate-800 mb-6">
        {totalCases > 0 && stages.map((stage) => {
          const pct = (stage.count / totalCases) * 100;
          if (pct === 0) return null;
          return (
            <div
              key={stage.label}
              style={{ width: `${pct}%` }}
              className={stage.color}
              title={`${stage.label}: ${stage.count} (${pct.toFixed(1)}%)`}
            />
          );
        })}
      </div>

      {/* Stage detail list */}
      <div className="space-y-3">
        {stages.map((stage) => (
          <div key={stage.label} className="flex items-center justify-between border-b border-slate-800/60 pb-2 text-xs">
            <div className="flex items-center gap-2">
              <span className={`h-2 w-2 rounded-full ${stage.color}`} />
              <span className="text-slate-300 font-medium">{stage.label}</span>
            </div>
            <div className="flex items-center gap-3">
              <span className="font-mono text-slate-200">{stage.count} cases</span>
              <span className="font-mono text-slate-400 text-[11px]">
                {totalCases > 0 ? formatPercent(stage.count / totalCases) : "0%"}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
