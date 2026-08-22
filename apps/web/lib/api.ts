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

export async function fetchPromises(status?: string): Promise<{ promises: any[]; count: number }> {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  const res = await fetch(`${API_BASE}/promises?${params.toString()}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch promises");
  return res.json();
}

export async function extractPromise(caseId: string, customerId: string, messageText: string): Promise<any> {
  const res = await fetch(`${API_BASE}/promises/extract`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ case_id: caseId, customer_id: customerId, message_text: messageText }),
  });
  if (!res.ok) throw new Error("Failed to extract promise");
  return res.json();
}

export async function fulfillPromise(promiseId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/promises/${promiseId}/fulfill`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to fulfill promise");
  return res.json();
}

export async function escalatePromise(promiseId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/promises/${promiseId}/escalate`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to escalate promise");
  return res.json();
}

export async function fetchPendingApprovals(): Promise<{ pending_approvals: any[]; count: number }> {
  const res = await fetch(`${API_BASE}/approvals`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch pending approvals");
  return res.json();
}

export async function submitApprovalDecision(
  caseId: string,
  decision: "APPROVE" | "REJECT" | "MODIFY",
  operatorId: string = "operator_admin",
  reason?: string,
  modifiedAmount?: number,
  modifiedAction?: string
): Promise<any> {
  const res = await fetch(`${API_BASE}/approvals/${caseId}/decision`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      decision,
      operator_id: operatorId,
      reason,
      modified_amount: modifiedAmount,
      modified_action: modifiedAction,
    }),
  });
  if (!res.ok) throw new Error("Failed to submit approval decision");
  return res.json();
}

export async function fetchActivePolicy(): Promise<any> {
  const res = await fetch(`${API_BASE}/policies/active`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch active policy");
  return res.json();
}

export async function fetchPolicies(): Promise<{ policies: any[]; count: number }> {
  const res = await fetch(`${API_BASE}/policies`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch policies");
  return res.json();
}

export async function createPolicyVersion(payload: any): Promise<any> {
  const res = await fetch(`${API_BASE}/policies`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Failed to create policy version");
  return res.json();
}

export async function runSimulation(count: number = 100, seed: number = 42): Promise<any> {
  const res = await fetch(`${API_BASE}/simulation/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ count, seed }),
  });
  if (!res.ok) throw new Error("Simulation run failed");
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
