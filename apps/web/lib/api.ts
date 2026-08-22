/**
 * Type-safe API client for RecoverAI backend.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export interface LedgerMetrics {
  total_revenue_at_risk: number;
  total_recoverable_revenue: number;
  total_recovered_revenue: number;
  recovery_rate_pct: number;
  active_cases_count: number;
  total_cases_count: number;
  status_counts: Record<string, number>;
  automated_actions_count: number;
  human_escalations_count: number;
  policy_blocked_actions_count: number;
  source_breakdown: Array<{
    source_type: string;
    amount_at_risk: number;
    recovered_amount: number;
    case_count: number;
    recovery_rate: number;
  }>;
  calculated_at: string;
}

export interface RecoveryCaseSummary {
  id: string;
  source_type: string;
  source_id: string;
  customer_id: string;
  customer_name: string;
  customer_segment: string;
  amount_at_risk: number;
  currency: string;
  recovery_probability: number;
  priority_score: number;
  risk_category: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  root_cause: string | null;
  recommended_action: string | null;
  status: string;
  recovered_amount: number;
  created_at: string;
  updated_at: string;
}

export interface CaseDetail {
  id: string;
  source_type: string;
  source_id: string;
  customer: {
    id: string;
    name: string;
    email: string;
    phone: string | null;
    segment: string;
    lifetime_value: number;
  } | null;
  amount_at_risk: number;
  currency: string;
  recovery_probability: number;
  priority_score: number;
  risk_category: string;
  root_cause: string | null;
  root_cause_explanation: string | null;
  recommended_action: string | null;
  recommended_channel: string | null;
  ai_reasoning: string | null;
  signals: {
    positive?: string[];
    negative?: string[];
  };
  status: string;
  stopping_reason: string | null;
  recovered_amount: number;
  actions: Array<{
    id: string;
    action_type: string;
    action_reason: string;
    policy_decision: string;
    policy_reason: string;
    status: string;
    payload: any;
    result: any;
    created_at: string;
  }>;
  attempts: Array<{
    id: string;
    attempt_number: number;
    action_type: string;
    result: string;
    attempted_at: string;
  }>;
  promises: Array<{
    id: string;
    promised_amount: number;
    promise_date: string;
    confidence: number;
    raw_text: string | null;
    status: string;
  }>;
  audit_logs: Array<{
    id: string;
    actor_type: string;
    actor_id: string | null;
    action: string;
    reason: string | null;
    metadata: any;
    created_at: string;
  }>;
  created_at: string;
  updated_at: string;
}

export async function fetchMetrics(): Promise<LedgerMetrics> {
  const res = await fetch(`${API_BASE}/ledger/metrics`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch ledger metrics");
  return res.json();
}

export async function fetchCases(params?: {
  status?: string;
  source_type?: string;
  risk_category?: string;
  search?: string;
  limit?: number;
}): Promise<{ cases: RecoveryCaseSummary[]; count: number }> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set("status", params.status);
  if (params?.source_type) searchParams.set("source_type", params.source_type);
  if (params?.risk_category) searchParams.set("risk_category", params.risk_category);
  if (params?.search) searchParams.set("search", params.search);
  if (params?.limit) searchParams.set("limit", params.limit.toString());

  const res = await fetch(`${API_BASE}/cases?${searchParams.toString()}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch cases");
  return res.json();
}

export async function fetchCaseDetail(caseId: string): Promise<CaseDetail> {
  const res = await fetch(`${API_BASE}/cases/${caseId}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch case ${caseId}`);
  return res.json();
}

export async function triggerAiDiagnosis(caseId: string): Promise<{ success: boolean; case: CaseDetail }> {
  const res = await fetch(`${API_BASE}/cases/${caseId}/diagnose`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) throw new Error("AI Diagnosis execution failed");
  return res.json();
}

export async function approveCase(caseId: string, reason?: string): Promise<{ success: boolean; status: string; recovered_amount: number }> {
  const params = new URLSearchParams();
  if (reason) params.set("reason", reason);

  const res = await fetch(`${API_BASE}/cases/${caseId}/approve?${params.toString()}`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Failed to approve recovery action");
  return res.json();
}

export async function rejectCase(caseId: string, reason?: string): Promise<{ success: boolean; status: string }> {
  const params = new URLSearchParams();
  if (reason) params.set("reason", reason);

  const res = await fetch(`${API_BASE}/cases/${caseId}/reject?${params.toString()}`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Failed to reject recovery action");
  return res.json();
}

export async function fetchAuditLogs(params?: { case_id?: string; actor_type?: string; limit?: number }): Promise<{ audit_logs: any[]; count: number }> {
  const searchParams = new URLSearchParams();
  if (params?.case_id) searchParams.set("case_id", params.case_id);
  if (params?.actor_type) searchParams.set("actor_type", params.actor_type);
  if (params?.limit) searchParams.set("limit", params.limit.toString());

  const res = await fetch(`${API_BASE}/ledger/audit?${searchParams.toString()}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch audit logs");
  return res.json();
}

export async function simulateWebhook(payload: any): Promise<any> {
  const res = await fetch(`${API_BASE}/webhooks/simulate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Webhook simulation failed");
  return res.json();
}
