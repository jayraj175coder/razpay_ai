"use client";

import { useEffect, useState } from "react";
import { Header } from "@/components/layout/header";
import { fetchAuditLogs } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import {
  History,
  FileText,
  Search,
  Filter,
  Shield,
  Bot,
  UserCheck,
  Cpu,
  RefreshCw,
  ChevronDown,
  ChevronRight,
} from "lucide-react";

export default function AuditTrailPage() {
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [caseFilter, setCaseFilter] = useState("");
  const [actorFilter, setActorFilter] = useState("ALL");
  const [expandedLogId, setExpandedLogId] = useState<string | null>(null);

  const loadLogs = async () => {
    try {
      setLoading(true);
      const res = await fetchAuditLogs({
        case_id: caseFilter || undefined,
        actor_type: actorFilter !== "ALL" ? actorFilter : undefined,
        limit: 100,
      });
      setLogs(res.audit_logs);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLogs();
  }, [actorFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loadLogs();
  };

  const getActorBadge = (actor: string) => {
    switch (actor) {
      case "AI_AGENT":
        return <span className="inline-flex items-center gap-1 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 text-[10px] font-mono font-semibold"><Bot className="h-3 w-3" /> AI Agent</span>;
      case "POLICY_ENGINE":
        return <span className="inline-flex items-center gap-1 rounded bg-blue-500/10 text-blue-300 border border-blue-500/20 px-2 py-0.5 text-[10px] font-mono font-semibold"><Shield className="h-3 w-3" /> Policy Engine</span>;
      case "HUMAN_OPERATOR":
        return <span className="inline-flex items-center gap-1 rounded bg-purple-500/10 text-purple-300 border border-purple-500/20 px-2 py-0.5 text-[10px] font-mono font-semibold"><UserCheck className="h-3 w-3" /> Operator</span>;
      case "WEBHOOK_SYSTEM":
        return <span className="inline-flex items-center gap-1 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20 px-2 py-0.5 text-[10px] font-mono font-semibold">Webhook</span>;
      default:
        return <span className="inline-flex items-center rounded bg-slate-800 text-slate-300 px-2 py-0.5 text-[10px] font-mono">{actor}</span>;
    }
  };

  return (
    <div className="flex flex-col flex-1 pb-16">
      <Header title="Immutable Audit Trail" />

      <div className="p-8 space-y-6 max-w-7xl">
        {/* Filter Bar */}
        <div className="flex flex-col gap-4 rounded-xl border border-slate-800 bg-slate-900/40 p-4 lg:flex-row lg:items-center lg:justify-between backdrop-blur-sm">
          <form onSubmit={handleSearchSubmit} className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search by Case ID (e.g. RCV-NX-1001)..."
              value={caseFilter}
              onChange={(e) => setCaseFilter(e.target.value)}
              className="w-full rounded-lg border border-slate-800 bg-slate-950/80 py-2 pl-9 pr-4 text-xs text-white placeholder-slate-400 focus:border-emerald-500 focus:outline-none"
            />
          </form>

          <div className="flex items-center gap-3">
            <select
              value={actorFilter}
              onChange={(e) => setActorFilter(e.target.value)}
              className="rounded-lg border border-slate-800 bg-slate-950/80 px-3 py-2 text-xs text-slate-300 focus:border-emerald-500 focus:outline-none"
            >
              <option value="ALL">All Actors</option>
              <option value="AI_AGENT">AI Agent</option>
              <option value="POLICY_ENGINE">Policy Engine</option>
              <option value="HUMAN_OPERATOR">Human Operator</option>
              <option value="WEBHOOK_SYSTEM">Webhook System</option>
              <option value="RECOVERY_EXECUTOR">Recovery Executor</option>
            </select>

            <button
              onClick={loadLogs}
              className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-700 hover:text-white transition"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} /> Refresh
            </button>
          </div>
        </div>

        {/* Audit Logs List */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 backdrop-blur-sm overflow-hidden">
          <div className="border-b border-slate-800 px-6 py-4 flex items-center justify-between">
            <h3 className="text-sm font-bold text-white">System & Decisioning Activity Log</h3>
            <span className="text-xs font-mono text-slate-400">{logs.length} Events Logged</span>
          </div>

          <div className="divide-y divide-slate-800/60">
            {logs.length === 0 ? (
              <div className="py-12 text-center text-xs text-slate-400">
                No audit log records match filter criteria.
              </div>
            ) : (
              logs.map((log) => {
                const isExpanded = expandedLogId === log.id;
                return (
                  <div
                    key={log.id}
                    className="p-5 hover:bg-slate-800/20 transition-colors cursor-pointer"
                    onClick={() => setExpandedLogId(isExpanded ? null : log.id)}
                  >
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-2">
                      <div className="flex items-center gap-3">
                        <button className="text-slate-400 hover:text-white">
                          {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                        </button>
                        {getActorBadge(log.actor_type)}
                        <span className="font-mono font-bold text-white text-xs">{log.action}</span>
                        {log.case_id && (
                          <span className="rounded bg-slate-800 px-2 py-0.5 text-[10px] font-mono text-slate-300">
                            {log.case_id}
                          </span>
                        )}
                      </div>
                      <span className="font-mono text-[11px] text-slate-400 pl-7 md:pl-0">
                        {formatDate(log.created_at)}
                      </span>
                    </div>

                    <div className="mt-2 pl-7 text-xs text-slate-300">
                      <p>{log.reason}</p>
                    </div>

                    {isExpanded && (
                      <div className="mt-3 ml-7 space-y-2">
                        {log.entry_hash && (
                          <div className="rounded-lg border border-emerald-500/20 bg-emerald-950/20 p-2.5 font-mono text-[11px] text-emerald-300">
                            <span className="text-[10px] text-emerald-400 font-bold uppercase tracking-wider block mb-1 flex items-center gap-1.5">
                              <Shield className="h-3 w-3" /> Cryptographic SHA-256 Hash Chain
                            </span>
                            <div className="flex flex-col gap-1 text-[10px]">
                              <div><span className="text-slate-400">Entry Hash: </span><span className="text-emerald-400 break-all">{log.entry_hash}</span></div>
                              {log.prev_hash && <div><span className="text-slate-400">Prev Hash: </span><span className="text-slate-400 break-all">{log.prev_hash}</span></div>}
                            </div>
                          </div>
                        )}
                        {log.metadata && (
                          <div className="rounded-lg border border-slate-800 bg-slate-950 p-3 font-mono text-[11px] text-slate-300 overflow-x-auto">
                            <span className="text-slate-400 text-[10px] uppercase block mb-1">Payload Metadata Diff:</span>
                            <pre className="text-emerald-400">{JSON.stringify(log.metadata, null, 2)}</pre>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
