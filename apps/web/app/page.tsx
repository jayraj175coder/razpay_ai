"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { ShieldCheck, ArrowRight, Activity, Cpu, Sparkles } from "lucide-react";

export default function HomePage() {
  const router = useRouter();

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-[#090d16] px-4 text-center">
      {/* Background subtle grid */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#1f29370f_1px,transparent_1px),linear-gradient(to_bottom,#1f29370f_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)] pointer-events-none" />

      <div className="relative z-10 max-w-3xl space-y-8">
        {/* Status Pill */}
        <div className="inline-flex items-center gap-2 rounded-full border border-emerald-500/20 bg-emerald-500/10 px-4 py-1.5 text-xs font-medium text-emerald-400 backdrop-blur-sm">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500"></span>
          </span>
          Razorpay AI Builder Challenge — Track 03: AI Revenue Recovery
        </div>

        {/* Hero Title */}
        <div className="space-y-4">
          <h1 className="text-4xl font-extrabold tracking-tight sm:text-6xl text-white">
            Recover<span className="text-emerald-400">AI</span>
          </h1>
          <p className="text-lg text-slate-400 sm:text-xl font-light max-w-2xl mx-auto">
            Detect revenue leakage. Decide the safest intervention. Recover the money. Prove the outcome.
          </p>
        </div>

        {/* Feature Highlights Grid */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3 text-left">
          <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4 backdrop-blur-sm">
            <div className="flex items-center gap-2 text-emerald-400 font-semibold text-sm mb-1">
              <Cpu className="h-4 w-4" /> LangGraph Reasoning
            </div>
            <p className="text-xs text-slate-400">
              Root-cause diagnosis and context-aware recovery strategy synthesis.
            </p>
          </div>

          <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4 backdrop-blur-sm">
            <div className="flex items-center gap-2 text-blue-400 font-semibold text-sm mb-1">
              <ShieldCheck className="h-4 w-4" /> Bounded Policy Engine
            </div>
            <p className="text-xs text-slate-400">
              Strict deterministic rules: retry caps, discount limits, stopping rules.
            </p>
          </div>

          <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4 backdrop-blur-sm">
            <div className="flex items-center gap-2 text-amber-400 font-semibold text-sm mb-1">
              <Activity className="h-4 w-4" /> Verified Ledger
            </div>
            <p className="text-xs text-slate-400">
              Every rupee recovered is reconciled in an immutable financial ledger.
            </p>
          </div>
        </div>

        {/* Launch Button */}
        <div className="pt-4 flex flex-col sm:flex-row items-center justify-center gap-4">
          <button
            onClick={() => router.push("/dashboard")}
            className="flex items-center gap-2 rounded-lg bg-emerald-500 px-6 py-3 text-sm font-semibold text-slate-950 transition hover:bg-emerald-400 active:scale-95 shadow-lg shadow-emerald-500/20"
          >
            Launch Command Center
            <ArrowRight className="h-4 w-4" />
          </button>
          
          <button
            onClick={() => router.push("/simulation")}
            className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800/80 px-6 py-3 text-sm font-semibold text-slate-200 transition hover:bg-slate-700 hover:text-white"
          >
            Run Recovery Simulation
          </button>
        </div>
      </div>
    </div>
  );
}
