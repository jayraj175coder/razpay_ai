"use client";

import { useEffect, useState } from "react";
import { Header } from "@/components/layout/header";
import { fetchPromises, extractPromise, fulfillPromise, escalatePromise } from "@/lib/api";
import { formatINR, formatDate } from "@/lib/utils";
import {
  CalendarCheck,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Send,
  MessageSquare,
  Sparkles,
  RefreshCw,
} from "lucide-react";

export default function PromisesPage() {
  const [promises, setPromises] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [extractText, setExtractText] = useState("Will settle the full ₹85,000 invoice on Monday afternoon.");
  const [caseIdInput, setCaseIdInput] = useState("RCV-KV-1003");
  const [customerIdInput, setCustomerIdInput] = useState("cust_vip_03");
  const [extracting, setExtracting] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);

  const loadPromises = async () => {
    try {
      setLoading(true);
      const res = await fetchPromises();
      setPromises(res.promises);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPromises();
  }, []);

  const handleExtract = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!extractText.trim()) return;

    setExtracting(true);
    try {
      const res = await extractPromise(caseIdInput, customerIdInput, extractText);
      if (res.has_promise) {
        setFeedback(`Extracted: ₹${res.promised_amount?.toLocaleString("en-IN")} due ${res.promise_date?.split("T")[0]} (${(res.confidence * 100).toFixed(0)}% confidence)`);
        await loadPromises();
      } else {
        setFeedback("No explicit promise detected in message.");
      }
    } catch (err: any) {
      alert(`Extraction failed: ${err.message}`);
    } finally {
      setExtracting(false);
    }
  };

  const handleFulfill = async (id: string) => {
    try {
      await fulfillPromise(id);
      setFeedback("Promise marked as FULFILLED and revenue reconciled!");
      await loadPromises();
    } catch (err: any) {
      alert(`Fulfillment failed: ${err.message}`);
    }
  };

  const handleEscalate = async (id: string) => {
    try {
      await escalatePromise(id);
      setFeedback("Promise escalated to human collections officer.");
      await loadPromises();
    } catch (err: any) {
      alert(`Escalation failed: ${err.message}`);
    }
  };

  const totalPromised = promises.reduce((sum, p) => sum + p.promised_amount, 0);
  const fulfilledValue = promises.filter((p) => p.status === "FULFILLED").reduce((sum, p) => sum + p.promised_amount, 0);
  const activeCount = promises.filter((p) => p.status === "WAITING" || p.status === "PROMISED").length;

  return (
    <div className="flex flex-col flex-1 pb-16">
      <Header title="Promise-to-Pay Tracker" />

      <div className="p-8 space-y-6 max-w-7xl">
        {/* KPI Row */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5 backdrop-blur-sm">
            <span className="text-xs uppercase tracking-wider text-slate-400 font-medium">Total Committed Value</span>
            <div className="mt-2 font-mono text-3xl font-extrabold text-white">
              {formatINR(totalPromised)}
            </div>
            <p className="text-xs text-slate-400 mt-1">{promises.length} promises recorded</p>
          </div>

          <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/[0.03] p-5 backdrop-blur-sm">
            <span className="text-xs uppercase tracking-wider text-slate-400 font-medium">Fulfilled Revenue</span>
            <div className="mt-2 font-mono text-3xl font-extrabold text-emerald-400">
              {formatINR(fulfilledValue)}
            </div>
            <p className="text-xs text-emerald-400/70 mt-1">Verified collected promises</p>
          </div>

          <div className="rounded-xl border border-amber-500/20 bg-amber-500/[0.03] p-5 backdrop-blur-sm">
            <span className="text-xs uppercase tracking-wider text-slate-400 font-medium">Active In-Flight Promises</span>
            <div className="mt-2 font-mono text-3xl font-extrabold text-amber-300">
              {activeCount}
            </div>
            <p className="text-xs text-slate-400 mt-1">Awaiting due dates</p>
          </div>
        </div>

        {/* Natural Language Promise Extractor Tool */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-6 backdrop-blur-sm space-y-4">
          <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
            <Sparkles className="h-5 w-5 text-emerald-400" />
            <div>
              <h2 className="text-sm font-bold text-white">AI Natural Language Promise Extractor</h2>
              <p className="text-xs text-slate-400">Extract amounts, target dates, and confidence from customer WhatsApp/Email text.</p>
            </div>
          </div>

          <form onSubmit={handleExtract} className="space-y-3">
            <div>
              <label className="text-xs text-slate-400 block mb-1">Customer Correspondence Message:</label>
              <textarea
                value={extractText}
                onChange={(e) => setExtractText(e.target.value)}
                rows={2}
                placeholder="e.g. I will transfer the pending Rs 85000 on Wednesday morning."
                className="w-full rounded-lg border border-slate-800 bg-slate-950 p-3 text-xs text-white placeholder-slate-500 focus:border-emerald-500 focus:outline-none"
              />
            </div>

            {/* Presets */}
            <div className="flex flex-wrap items-center gap-2 text-[11px] text-slate-400">
              <span>Try Presets:</span>
              <button
                type="button"
                onClick={() => setExtractText("Our accountant is back on Friday, will clear the pending 125000 by 5 PM.")}
                className="rounded bg-slate-800 px-2 py-0.5 text-slate-300 hover:bg-slate-700 hover:text-white"
              >
                ₹1,25,000 on Friday
              </button>
              <button
                type="button"
                onClick={() => setExtractText("Card limit increased, paying 24500 tomorrow morning.")}
                className="rounded bg-slate-800 px-2 py-0.5 text-slate-300 hover:bg-slate-700 hover:text-white"
              >
                ₹24,500 tomorrow
              </button>
            </div>

            <div className="flex items-center justify-between pt-2">
              {feedback && (
                <span className="text-xs font-semibold text-emerald-400 flex items-center gap-1.5">
                  <CheckCircle2 className="h-4 w-4" />
                  {feedback}
                </span>
              )}
              <button
                type="submit"
                disabled={extracting}
                className="ml-auto flex items-center gap-2 rounded-lg bg-emerald-500 px-4 py-2 text-xs font-bold text-slate-950 hover:bg-emerald-400 transition disabled:opacity-50"
              >
                <Sparkles className="h-3.5 w-3.5" />
                {extracting ? "Extracting..." : "Extract & Track Promise"}
              </button>
            </div>
          </form>
        </div>

        {/* Promises Table */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 backdrop-blur-sm overflow-hidden">
          <div className="flex items-center justify-between border-b border-slate-800 px-6 py-4">
            <div>
              <h3 className="text-sm font-bold text-white">Tracked Promises</h3>
              <p className="text-xs text-slate-400">Lifecycle monitoring from promise commitment to verified fulfillment</p>
            </div>
            <button
              onClick={loadPromises}
              className="flex items-center gap-1 text-xs text-slate-400 hover:text-white"
            >
              <RefreshCw className={`h-3 w-3 ${loading ? "animate-spin" : ""}`} /> Refresh
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-900/80 text-[11px] font-semibold uppercase tracking-wider text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="py-3 px-6">Customer & Case</th>
                  <th className="py-3 px-4">Promised Amount</th>
                  <th className="py-3 px-4">Due Date</th>
                  <th className="py-3 px-4">Customer Raw Message</th>
                  <th className="py-3 px-4">Confidence</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-6 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-medium text-slate-200">
                {promises.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-8 text-center text-xs text-slate-400">
                      No active promises tracked.
                    </td>
                  </tr>
                ) : (
                  promises.map((p) => (
                    <tr key={p.id} className="hover:bg-slate-800/30">
                      <td className="py-3.5 px-6">
                        <div className="flex flex-col">
                          <span className="font-bold text-white">{p.customer_name}</span>
                          <span className="font-mono text-[10px] text-slate-400">{p.case_id}</span>
                        </div>
                      </td>

                      <td className="py-3.5 px-4 font-mono font-bold text-white text-sm">
                        {formatINR(p.promised_amount)}
                      </td>

                      <td className="py-3.5 px-4 font-mono text-xs">
                        <span className="block text-slate-200">{formatDate(p.promise_date)}</span>
                        {p.days_remaining !== undefined && p.status === "WAITING" && (
                          <span className={`text-[10px] ${p.days_remaining < 0 ? "text-rose-400" : "text-slate-400"}`}>
                            {p.days_remaining < 0 ? `${Math.abs(p.days_remaining)} days overdue` : `${p.days_remaining} days left`}
                          </span>
                        )}
                      </td>

                      <td className="py-3.5 px-4 max-w-xs text-slate-300 truncate text-[11px]">
                        "{p.raw_text}"
                      </td>

                      <td className="py-3.5 px-4 font-mono text-xs text-emerald-400">
                        {(p.confidence * 100).toFixed(0)}%
                      </td>

                      <td className="py-3.5 px-4">
                        <span
                          className={`rounded-full px-2 py-0.5 text-[10px] font-mono font-semibold ${
                            p.status === "FULFILLED"
                              ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                              : p.status === "WAITING"
                              ? "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                              : "bg-rose-500/20 text-rose-300 border border-rose-500/30"
                          }`}
                        >
                          {p.status}
                        </span>
                      </td>

                      <td className="py-3.5 px-6 text-right">
                        {p.status === "WAITING" && (
                          <div className="flex items-center justify-end gap-2">
                            <button
                              onClick={() => handleFulfill(p.id)}
                              className="rounded bg-emerald-500/20 border border-emerald-500/40 px-2 py-1 text-[11px] font-semibold text-emerald-300 hover:bg-emerald-500/30 transition"
                            >
                              Fulfill
                            </button>
                            <button
                              onClick={() => handleEscalate(p.id)}
                              className="rounded bg-rose-500/20 border border-rose-500/40 px-2 py-1 text-[11px] font-semibold text-rose-300 hover:bg-rose-500/30 transition"
                            >
                              Escalate
                            </button>
                          </div>
                        )}
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
