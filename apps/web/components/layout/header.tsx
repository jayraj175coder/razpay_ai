"use client";

import { useState } from "react";
import { PlusCircle, RefreshCw, CheckCircle2, Shield } from "lucide-react";
import { simulateWebhook } from "@/lib/api";

export function Header({ title }: { title: string }) {
  const [isSimulating, setIsSimulating] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);

  const handleQuickInject = async (type: "invoice" | "subscription" | "payment") => {
    setIsSimulating(true);
    try {
      if (type === "invoice") {
        await simulateWebhook({
          event: "invoice.overdue",
          invoice: { amount: 85000.0, overdue_days: 14 },
          customer: { name: "Apex Logistics India", email: "billing@apexlogistics.in", segment: "SMB" },
        });
      } else if (type === "subscription") {
        await simulateWebhook({
          event: "subscription.payment_failed",
          subscription: { amount: 14999.0 },
          customer: { name: "DevMatrix SaaS", email: "finance@devmatrix.io", segment: "SMB" },
        });
      } else {
        await simulateWebhook({
          event: "payment.failed",
          payment: { entity: { amount: 6500000, currency: "INR", error_code: "insufficient_funds", email: "rohit.varma@tcs.in" } },
          customer: { name: "Rohit Varma", email: "rohit.varma@tcs.in", segment: "VIP", lifetime_value: 350000.0 },
        });
      }
      setFeedback("Event ingested successfully!");
      setTimeout(() => {
        setFeedback(null);
        window.location.reload();
      }, 800);
    } catch (err: any) {
      setFeedback(`Error: ${err.message}`);
    } finally {
      setIsSimulating(false);
    }
  };

  return (
    <header className="sticky top-0 z-20 flex h-16 w-full items-center justify-between border-b border-slate-800 bg-[#090d16]/80 px-8 backdrop-blur-md">
      <div>
        <h1 className="text-lg font-bold tracking-tight text-white">{title}</h1>
      </div>

      <div className="flex items-center gap-3">
        {feedback && (
          <span className="flex items-center gap-1.5 text-xs text-emerald-400 font-medium animate-fade-in">
            <CheckCircle2 className="h-3.5 w-3.5" />
            {feedback}
          </span>
        )}

        {/* Quick event simulation trigger buttons */}
        <div className="flex items-center gap-1.5 rounded-lg border border-slate-800 bg-slate-900/80 p-1">
          <span className="px-2 text-[10px] font-mono uppercase text-slate-400">Simulate:</span>
          <button
            disabled={isSimulating}
            onClick={() => handleQuickInject("invoice")}
            className="rounded bg-slate-800 px-2.5 py-1 text-xs font-medium text-slate-200 hover:bg-slate-700 hover:text-white transition disabled:opacity-50"
          >
            + B2B Invoice
          </button>
          <button
            disabled={isSimulating}
            onClick={() => handleQuickInject("subscription")}
            className="rounded bg-slate-800 px-2.5 py-1 text-xs font-medium text-slate-200 hover:bg-slate-700 hover:text-white transition disabled:opacity-50"
          >
            + Sub Dunning
          </button>
          <button
            disabled={isSimulating}
            onClick={() => handleQuickInject("payment")}
            className="rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 px-2.5 py-1 text-xs font-semibold hover:bg-emerald-500/30 transition disabled:opacity-50"
          >
            + Failed ₹65k
          </button>
        </div>

        {/* System Pill */}
        <div className="hidden sm:inline-flex items-center gap-1.5 rounded-full border border-slate-800 bg-slate-900 px-3 py-1 text-xs text-slate-400">
          <Shield className="h-3.5 w-3.5 text-emerald-400" />
          <span className="font-mono text-[11px]">Policy v1 Enforced</span>
        </div>
      </div>
    </header>
  );
}
