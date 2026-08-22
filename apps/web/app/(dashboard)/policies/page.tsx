"use client";

import { useEffect, useState } from "react";
import { Header } from "@/components/layout/header";
import { fetchActivePolicy, fetchPolicies, createPolicyVersion } from "@/lib/api";
import { formatINR, formatDate } from "@/lib/utils";
import {
  ShieldAlert,
  ShieldCheck,
  CheckCircle2,
  Lock,
  Plus,
  History,
  Sliders,
  AlertOctagon,
  RefreshCw,
} from "lucide-react";

export default function PoliciesPage() {
  const [activePolicy, setActivePolicy] = useState<any | null>(null);
  const [policies, setPolicies] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);

  // Form state
  const [name, setName] = useState("Enterprise Standard Policy");
  const [maxRetries, setMaxRetries] = useState(3);
  const [maxMessages, setMaxMessages] = useState(2);
  const [commWindowHours, setCommWindowHours] = useState(168);
  const [maxDiscount, setMaxDiscount] = useState(5.0);
  const [humanThreshold, setHumanThreshold] = useState(100000.0);
  const [retryDelay, setRetryDelay] = useState(24);

  const loadPolicyData = async () => {
    try {
      setLoading(true);
      const [active, list] = await Promise.all([fetchActivePolicy(), fetchPolicies()]);
      setActivePolicy(active);
      setPolicies(list.policies);
      if (active) {
        setName(active.name);
        setMaxRetries(active.max_payment_retries);
        setMaxMessages(active.max_messages);
        setCommWindowHours(active.communication_window_hours);
        setMaxDiscount(active.max_discount_pct);
        setHumanThreshold(active.human_approval_threshold);
        setRetryDelay(active.retry_delay_hours);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPolicyData();
  }, []);

  const handlePublish = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const res = await createPolicyVersion({
        name,
        max_payment_retries: Number(maxRetries),
        max_messages: Number(maxMessages),
        communication_window_hours: Number(commWindowHours),
        max_discount_pct: Number(maxDiscount),
        human_approval_threshold: Number(humanThreshold),
        retry_delay_hours: Number(retryDelay),
        escalation_delay_hours: 72,
      });
      setFeedback(`Policy v${res.version} published and set as active!`);
      await loadPolicyData();
    } catch (err: any) {
      alert(`Publishing failed: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex flex-col flex-1 pb-16">
      <Header title="Bounded Policy Engine" />

      <div className="p-8 space-y-6 max-w-7xl">
        {/* Policy Philosophy Banner */}
        <div className="rounded-xl border border-blue-500/30 bg-blue-500/10 p-5 backdrop-blur-sm flex items-start gap-4">
          <ShieldAlert className="h-6 w-6 text-blue-400 shrink-0 mt-0.5" />
          <div>
            <h2 className="text-sm font-bold text-white">Deterministic Financial Safeguards</h2>
            <p className="text-xs text-blue-300/80 mt-0.5 leading-relaxed">
              AI agents propose recovery strategies, but the Policy Engine strictly enforces deterministic bounds.
              No action exceeding retry limits, frequency caps, or financial thresholds can execute without explicit governance.
            </p>
          </div>
        </div>

        {feedback && (
          <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3 text-xs font-medium text-emerald-300 flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4" />
            {feedback}
          </div>
        )}

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* Policy Editor Form */}
          <div className="lg:col-span-2 rounded-xl border border-slate-800 bg-slate-900/40 p-6 backdrop-blur-sm space-y-5">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div>
                <h3 className="text-sm font-bold text-white">Policy Parameters & Bounds</h3>
                <p className="text-xs text-slate-400">Configure financial rules for active policy enforcement</p>
              </div>
              {activePolicy && (
                <span className="rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 px-2.5 py-0.5 text-xs font-mono font-bold">
                  Active: v{activePolicy.version}
                </span>
              )}
            </div>

            <form onSubmit={handlePublish} className="space-y-4">
              <div>
                <label className="text-xs text-slate-400 block mb-1">Policy Profile Name:</label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full rounded-lg border border-slate-800 bg-slate-950 p-2.5 text-xs text-white focus:border-emerald-500 focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Max Payment Retries per Cycle:</label>
                  <input
                    type="number"
                    min={1}
                    max={10}
                    value={maxRetries}
                    onChange={(e) => setMaxRetries(parseInt(e.target.value) || 1)}
                    className="w-full rounded-lg border border-slate-800 bg-slate-950 p-2.5 text-xs font-mono text-white focus:border-emerald-500 focus:outline-none"
                  />
                  <span className="text-[10px] text-slate-400 mt-1 block">Default: 3 attempts</span>
                </div>

                <div>
                  <label className="text-xs text-slate-400 block mb-1">Max Reminder Frequency:</label>
                  <input
                    type="number"
                    min={1}
                    max={10}
                    value={maxMessages}
                    onChange={(e) => setMaxMessages(parseInt(e.target.value) || 1)}
                    className="w-full rounded-lg border border-slate-800 bg-slate-950 p-2.5 text-xs font-mono text-white focus:border-emerald-500 focus:outline-none"
                  />
                  <span className="text-[10px] text-slate-400 mt-1 block">Max messages per 7-day window</span>
                </div>

                <div>
                  <label className="text-xs text-slate-400 block mb-1">Human Approval Threshold (INR):</label>
                  <input
                    type="number"
                    step={1000}
                    value={humanThreshold}
                    onChange={(e) => setHumanThreshold(parseFloat(e.target.value) || 0)}
                    className="w-full rounded-lg border border-slate-800 bg-slate-950 p-2.5 text-xs font-mono text-white focus:border-emerald-500 focus:outline-none"
                  />
                  <span className="text-[10px] text-slate-400 mt-1 block">Txns above this require operator sign-off</span>
                </div>

                <div>
                  <label className="text-xs text-slate-400 block mb-1">Max Discount Allowance (%):</label>
                  <input
                    type="number"
                    step={0.5}
                    min={0}
                    max={50}
                    value={maxDiscount}
                    onChange={(e) => setMaxDiscount(parseFloat(e.target.value) || 0)}
                    className="w-full rounded-lg border border-slate-800 bg-slate-950 p-2.5 text-xs font-mono text-white focus:border-emerald-500 focus:outline-none"
                  />
                  <span className="text-[10px] text-slate-400 mt-1 block">Cart dropoff incentive ceiling</span>
                </div>
              </div>

              {/* Security Blocklist Preview */}
              <div className="rounded-lg border border-slate-800 bg-slate-950 p-3 space-y-2">
                <span className="text-[11px] font-mono text-slate-400 uppercase flex items-center gap-1.5">
                  <Lock className="h-3.5 w-3.5 text-rose-400" />
                  Hardcoded Security Disallowed Codes (Zero Auto-Retry):
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {["fraud_suspected", "stolen_card", "account_frozen", "sanction_block"].map((code) => (
                    <span key={code} className="rounded bg-rose-500/10 text-rose-400 border border-rose-500/20 px-2 py-0.5 text-[10px] font-mono font-semibold">
                      {code}
                    </span>
                  ))}
                </div>
              </div>

              <div className="flex justify-end pt-2">
                <button
                  type="submit"
                  disabled={saving}
                  className="flex items-center gap-2 rounded-lg bg-emerald-500 px-5 py-2 text-xs font-bold text-slate-950 hover:bg-emerald-400 transition disabled:opacity-50 shadow-md shadow-emerald-500/20"
                >
                  <Plus className="h-4 w-4" />
                  {saving ? "Publishing..." : "Publish New Policy Version"}
                </button>
              </div>
            </form>
          </div>

          {/* Policy Version History */}
          <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-6 backdrop-blur-sm space-y-4">
            <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
              <History className="h-4 w-4 text-emerald-400" />
              <h3 className="text-sm font-bold text-white">Version History</h3>
            </div>

            <div className="space-y-3">
              {policies.map((p) => (
                <div
                  key={p.id}
                  className={`p-3 rounded-lg border text-xs transition ${
                    p.is_active
                      ? "border-emerald-500/30 bg-emerald-500/5 text-white"
                      : "border-slate-800 bg-slate-950/40 text-slate-400"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono font-bold text-white">v{p.version} — {p.name}</span>
                    {p.is_active && (
                      <span className="rounded bg-emerald-500/20 text-emerald-300 text-[10px] font-mono px-1.5 py-0.5">
                        Active
                      </span>
                    )}
                  </div>
                  <div className="mt-2 space-y-1 text-[11px] font-mono text-slate-400">
                    <div>Max Retries: {p.max_payment_retries}</div>
                    <div>Approval Threshold: {formatINR(p.human_approval_threshold)}</div>
                    <div>Max Discount: {p.max_discount_pct}%</div>
                    <div className="text-[10px] text-slate-500 pt-1">{formatDate(p.created_at)}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
